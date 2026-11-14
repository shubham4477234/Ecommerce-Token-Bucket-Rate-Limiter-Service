
from django.db.models import Prefetch
import hashlib
import json
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from seller.models import SellerProduct, ProductLine, Category

from .serializers import CustomerProductListSerializer, CustomerProductDetailSerializer, CustomerCategorySerializer
from .pagination import CustomerProductPagination
from config.cache_utils import (
    CUSTOMER_PRODUCT_LIST_VERSION_KEY,
)
from customer.models import Cart
from customer.serializers import CartSerializer


class CustomerProductListView(ListAPIView):

    serializer_class = CustomerProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomerProductPagination

    def get_queryset(self):

        # Get active variants that have stock available
        available_variants = (
            ProductLine.objects
            .filter(
                is_active=True,
                stock_qty__gt=0
            )
            .prefetch_related(
                "attribute_values__attribute_value__attribute"
            )
            .order_by("id")
        )

        # Get active and verified seller product listings
        return (
            SellerProduct.objects
            .filter(
                is_active=True,
                product__is_active=True,
                product__category__is_active=True,
                product__product_type__is_active=True,
                seller__is_active=True,
                seller__verification_status="verified",
                product_lines__is_active=True,
                product_lines__stock_qty__gt=0,
            )
            .select_related(
                "product",
                "product__category",
                "product__product_type",
                "seller",
            )
            .prefetch_related(
                "images",
                Prefetch(
                    "product_lines",
                    queryset=available_variants,
                    to_attr="available_product_lines",
                ),
            )
            .distinct()
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):

        # Get current listing cache version
        version = cache.get(
            CUSTOMER_PRODUCT_LIST_VERSION_KEY,
            1
        )

        # Include query parameters in cache key
        query_string = request.GET.urlencode()

        query_hash = hashlib.md5(
            query_string.encode()
        ).hexdigest()

        # Include domain and protocol in cache key
        request_host = request.build_absolute_uri("/")

        cache_key = (
            f"customer:products:list:"
            f"{request_host}:v{version}:{query_hash}"
        )

        # Check Redis cache
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        # Cache miss: fetch data from PostgreSQL
        response = super().list(
            request,
            *args,
            **kwargs
        )

        # Convert response into JSON-compatible data
        response_data = response.data

        cache_data = json.loads(
            JSONRenderer().render(response_data)
        )

        # Store response in Redis for 120 seconds
        cache.set(
            cache_key,
            cache_data,
            timeout=120
        )

        return Response(response_data)



class CustomerProductDetailView(RetrieveAPIView):

    serializer_class = CustomerProductDetailSerializer
    permission_classes = [AllowAny]

    lookup_field = "id"

    def get_queryset(self):

        # Get all active variants, including out-of-stock variants
        available_variants = (
            ProductLine.objects
            .filter(
                is_active=True
            )
            .prefetch_related(
                "attribute_values__attribute_value__attribute"
            )
            .order_by("id")
        )

        # Get active and verified seller product listings
        return (
            SellerProduct.objects
            .filter(
                is_active=True,
                product__is_active=True,
                product__category__is_active=True,
                product__product_type__is_active=True,
                seller__is_active=True,
                seller__verification_status="verified",
            )
            .select_related(
                "product",
                "product__category",
                "product__product_type",
                "seller",
            )
            .prefetch_related(
                "images",
                Prefetch(
                    "product_lines",
                    queryset=available_variants,
                    to_attr="detail_product_lines",
                ),
            )
        )

    
def retrieve(self, request, *args, **kwargs):

    # Get seller product listing ID
    seller_product_id = kwargs["pk"]

    # Include domain and protocol in cache key
    request_host = request.build_absolute_uri("/")

    # Get the current cache version for this listing
    detail_version_key = (
        f"customer:products:detail:version:{seller_product_id}"
    )

    version = cache.get(detail_version_key, 1)

    # Create a host-aware and versioned cache key
    cache_key = (
        f"customer:products:detail:"
        f"{request_host}:{seller_product_id}:v{version}"
    )

    # Check Redis cache
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return Response(cached_data)

    # Cache miss: fetch product details from PostgreSQL
    response = super().retrieve(
        request,
        *args,
        **kwargs
    )

    # Convert response into JSON-compatible data
    cache_data = json.loads(
        JSONRenderer().render(response.data)
    )

    # Store response in Redis for 5 minutes
    cache.set(
        cache_key,
        cache_data,
        timeout=300
    )

    return Response(response.data)


class CustomerCategoryListView(ListAPIView):

    serializer_class = CustomerCategorySerializer
    permission_classes = [AllowAny]

    CACHE_KEY = "customer:categories:tree"
    CACHE_TIMEOUT = 600  # 10 minutes

    def list(self, request, *args, **kwargs):

        # Check Redis first
        cached_data = cache.get(self.CACHE_KEY)

        if cached_data is not None:
            return Response(cached_data)

        # Fetch active categories
        categories = Category.objects.filter(
            is_active=True
        ).order_by("tree_id", "lft")

        # Load the complete category tree efficiently
        categories = categories.get_cached_trees()

        # Serialize categories
        serializer = self.get_serializer(
            categories,
            many=True
        )

        # Save response in Redis
        cache.set(
            self.CACHE_KEY,
            serializer.data,
            timeout=self.CACHE_TIMEOUT
        )

        return Response(serializer.data)



class CustomerCartView(RetrieveAPIView):

    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):

        customer_id = request.user.id

        cache_key = f"customer:cart:{customer_id}"

        # Check Redis first
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        # Get customer's cart from database
        cart, created = Cart.objects.get_or_create(
            customer=request.user
        )

        # Fetch cart items efficiently
        cart = Cart.objects.prefetch_related(
            "items__product_line__seller_product__product",
            "items__product_line__seller_product__seller"
        ).get(id=cart.id)

        # Serialize cart
        serializer = self.get_serializer(cart)

        # Store response in Redis
        cache.set(
            cache_key,
            serializer.data,
            timeout=300
        )

        return Response(serializer.data)