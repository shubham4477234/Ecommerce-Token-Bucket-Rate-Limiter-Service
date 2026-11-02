from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSeller
from .models import (
    SellerProfile,
    Category,
    ProductType,
    ProductTypeAttribute,
    Product, SellerProduct
)
from .serializers import (
    SellerProfileSerializer,
    CategorySerializer,
    ProductTypeSerializer,
    ProductTypeAttributeSerializer,
    ProductRequestSerializer,
    ProductSerializer, AddProductToStoreSerializer, SellerProductListSerializer
)

class SellerProfileView(APIView):

    permission_classes = [IsAuthenticated, IsSeller]

    # CREATE SELLER PROFILE
    def post(self, request):

        # Check whether the seller already has a profile
        if SellerProfile.objects.filter(user=request.user).exists():
            raise ValidationError(
                {"message": "Seller profile already exists."}
            )

        # Validate the incoming data
        serializer = SellerProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save profile and connect it to logged-in user
        serializer.save(user=request.user)

        # Remove old cached data
        cache.delete(f"seller:profile:{request.user.id}")

        return Response(
            {
                "message": "Seller profile created successfully.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    # GET SELLER PROFILE
    def get(self, request):

        # Create a unique Redis key for this seller
        cache_key = f"seller:profile:{request.user.id}"

        # First check Redis
        profile_data = cache.get(cache_key)

        if profile_data:
            return Response(profile_data, status=status.HTTP_200_OK)

        # If data is not in Redis, get it from PostgreSQL
        profile = get_object_or_404(
            SellerProfile,
            user=request.user
        )

        serializer = SellerProfileSerializer(profile)

        # Store the response in Redis for 5 minutes
        cache.set(cache_key, serializer.data, 300)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # UPDATE SELLER PROFILE
    def patch(self, request):

        # Get the logged-in seller's profile
        profile = get_object_or_404(
            SellerProfile,
            user=request.user
        )

        # Update only the fields sent by the frontend
        serializer = SellerProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Delete old Redis data so the next GET fetches fresh data
        cache.delete(f"seller:profile:{request.user.id}")

        return Response(
            {
                "message": "Seller profile updated successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


class CategoryListView(APIView):

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):

        # Redis key for category hierarchy
        cache_key = "seller:categories:tree"

        # Check Redis first
        categories = cache.get(cache_key)

        if categories is not None:
            return Response(
                {"categories": categories},
                status=status.HTTP_200_OK
            )

        # Get active parent categories
        parent_categories = Category.objects.filter(
            parent__isnull=True,
            is_active=True
        )

        # Convert categories into nested JSON
        serializer = CategorySerializer(
            parent_categories,
            many=True
        )

        # Save the response in Redis for 10 minutes
        categories = serializer.data
        cache.set(cache_key, categories, 600)

        return Response(
            {"categories": categories},
            status=status.HTTP_200_OK
        )

class ProductTypeListView(APIView):

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):

        # Redis cache key
        cache_key = "seller:product-types:list"

        # Check Redis first
        product_types = cache.get(cache_key)

        if product_types is not None:
            return Response(
                {"product_types": product_types},
                status=status.HTTP_200_OK
            )

        # Get all active product types
        product_types = ProductType.objects.filter(
            is_active=True
        )

        # Convert database objects into JSON
        serializer = ProductTypeSerializer(
            product_types,
            many=True
        )

        # Save data in Redis for 10 minutes
        product_types = serializer.data
        cache.set(cache_key, product_types, 600)

        return Response(
            {"product_types": product_types},
            status=status.HTTP_200_OK
        )

class ProductTypeAttributeView(APIView):

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request, product_type_id):

        # Check whether the product type exists and is active
        product_type = get_object_or_404(
            ProductType,
            id=product_type_id,
            is_active=True
        )

        # Create a separate Redis key for each product type
        cache_key = f"seller:product-type:{product_type_id}:attributes"

        # Check Redis first
        attributes = cache.get(cache_key)

        if attributes is not None:
            return Response(
                {
                    "product_type": product_type.name,
                    "attributes": attributes
                },
                status=status.HTTP_200_OK
            )

        # Get attributes connected to this product type
        product_attributes = ProductTypeAttribute.objects.filter(
            product_type=product_type,
            attribute__is_active=True
        ).select_related(
            "attribute"
        ).prefetch_related(
            "attribute__values"
        )

        # Convert the data into JSON
        serializer = ProductTypeAttributeSerializer(
            product_attributes,
            many=True
        )

        attributes = serializer.data

        # Store the response in Redis for 10 minutes
        cache.set(cache_key, attributes, 600)

        return Response(
            {
                "product_type": product_type.name,
                "attributes": attributes
            },
            status=status.HTTP_200_OK
        )

class ProductCatalogueView(APIView):

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):

        # Get search and category filters from frontend
        search = request.query_params.get("search", "")
        category_slug = request.query_params.get("category", "")
        page = request.query_params.get("page", "1")

        # Create Redis key using the request filters
        cache_key = (
            f"seller:catalog:products:"
            f"{search}:{category_slug}:{page}"
        )

        # Check Redis first
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(
                cached_data,
                status=status.HTTP_200_OK
            )

        # Get all active catalogue products
        products = Product.objects.filter(
            is_active=True,
            category__is_active=True
        ).select_related(
            "category",
            "product_type"
        )

        # Search products by name or description
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        # Filter by selected category and its subcategories
        if category_slug:

            category = get_object_or_404(
                Category,
                slug=category_slug,
                is_active=True
            )

            categories = category.get_descendants(
                include_self=True
            ).filter(is_active=True)

            products = products.filter(
                category__in=categories
            )

        # Show newest products first
        products = products.order_by("-created_at")

        # Create pagination
        paginator = PageNumberPagination()
        paginator.page_size = 20

        product_page = paginator.paginate_queryset(
            products,
            request
        )

        # Convert products into JSON
        serializer = ProductSerializer(
            product_page,
            many=True
        )

        # Create paginated response
        response = paginator.get_paginated_response(
            serializer.data
        )

        # Cache the response for 5 minutes
        cache.set(cache_key, response.data, 300)

        return response


class ProductRequestView(APIView):

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request):

        # Get the logged-in seller's store
        seller_profile = get_object_or_404(
            SellerProfile,
            user=request.user
        )

        # Validate the submitted product details
        serializer = ProductRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save the request with the logged-in seller
        serializer.save(seller=seller_profile)

        return Response(
            {
                "message": "Product request submitted successfully. Waiting for admin approval.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )



class AddProductToStoreView(APIView):

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):

        # Get the logged-in seller's store
        seller_profile = get_object_or_404(
            SellerProfile,
            user=request.user
        )

        # Create a separate cache key for each seller
        cache_key = f"seller:products:{seller_profile.id}"

        # Check Redis cache first
        products_data = cache.get(cache_key)

        if products_data is not None:
            return Response(
                {
                    "message": "Your store products fetched successfully.",
                    "data": products_data
                },
                status=status.HTTP_200_OK
            )

        # Fetch only this seller's products
        products = SellerProduct.objects.filter(
            seller=seller_profile
        ).select_related(
            "product",
            "product__category",
            "product__product_type"
        ).order_by("-created_at")

        # Serialize the products
        serializer = SellerProductListSerializer(
            products,
            many=True
        )

        # Store the response in cache for 5 minutes
        cache.set(cache_key, serializer.data, 300)

        return Response(
            {
                "message": "Your store products fetched successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):

        # Get the logged-in seller's store
        seller_profile = get_object_or_404(
            SellerProfile,
            user=request.user
        )

        # Validate the product ID
        serializer = AddProductToStoreSerializer(
            data=request.data,
            context={"seller": seller_profile}
        )

        serializer.is_valid(raise_exception=True)

        # Create the SellerProduct record
        seller_product = serializer.save(seller=seller_profile)

        # Clear cached seller product list
        cache.delete(f"seller:products:{seller_profile.id}")

        return Response(
            {
                "message": "Product added to your store successfully.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
