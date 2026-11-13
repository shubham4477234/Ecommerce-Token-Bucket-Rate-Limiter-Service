
from django.db.models import Prefetch
import hashlib
import json
from django.core.cache import cache

from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from seller.models import SellerProduct, ProductLine

from .serializers import CustomerProductListSerializer, CustomerProductDetailSerializer
from .pagination import CustomerProductPagination
from config.cache_utils import (
    CUSTOMER_PRODUCT_LIST_VERSION_KEY,
)


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
