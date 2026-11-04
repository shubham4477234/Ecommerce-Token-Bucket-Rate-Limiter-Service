from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.core.exceptions import ValidationError
from .services import approve_product_request, reject_product_request, update_category, create_product_type, configure_product_attributes
from accounts.permissions import IsAdmin
from seller.models import ProductRequest, Category, ProductType, ProductTypeAttribute
from .serializers import AdminProductTypeSerializer,AdminProductRequestSerializer, AdminCategorySerializer, AdminCategoryUpdateSerializer, AdminProductTypeAttributeResponseSerializer, AdminAttributeConfigurationSerializer
from django.shortcuts import get_object_or_404
from django.core.cache import cache
class AdminProductRequestListView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):

        # Get all pending product requests
        product_requests = ProductRequest.objects.filter(
            status="pending"
        ).select_related(
            "seller",
            "category",
            "product_type"
        ).order_by("-created_at")

        # Serialize the requests
        serializer = AdminProductRequestSerializer(
            product_requests,
            many=True
        )

        return Response({
            "message": "Pending product requests fetched successfully.",
            "total_requests": product_requests.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class AdminProductRequestDetailView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, pk):

        # Get the product request using its ID
        product_request = get_object_or_404(
            ProductRequest.objects.select_related(
                "seller",
                "category",
                "product_type"
            ),
            id=pk
        )

        # Serialize the request details
        serializer = AdminProductRequestSerializer(
            product_request
        )

        return Response({
            "message": "Product request details fetched successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class AdminApproveProductRequestView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):

        # Find the requested product
        product_request = get_object_or_404(
            ProductRequest.objects.select_related(
                "seller",
                "category",
                "product_type"
            ),
            id=pk
        )

        try:

            # Approve the request and create the product
            product = approve_product_request(product_request)

            return Response({
                "message": "Product request approved successfully.",
                "data": {
                    "request_id": product_request.id,
                    "request_status": product_request.status,
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_slug": product.slug,
                    "product_pid": product.pid
                }
            }, status=status.HTTP_200_OK)

        except ValidationError as error:

            return Response({
                "message": "Product approval failed.",
                "errors": error.messages
            }, status=status.HTTP_400_BAD_REQUEST)

class AdminRejectProductRequestView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):

        # Get the product request
        product_request = get_object_or_404(
            ProductRequest,
            id=pk
        )

        # Get rejection reason from request body
        admin_note = request.data.get("admin_note", "").strip()

        # Validate rejection reason
        if not admin_note:
            return Response({
                "message": "Rejection reason is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:

            # Reject the product request
            rejected_request = reject_product_request(
                product_request,
                admin_note
            )

            return Response({
                "message": "Product request rejected successfully.",
                "data": {
                    "request_id": rejected_request.id,
                    "product_name": rejected_request.name,
                    "status": rejected_request.status,
                    "admin_note": rejected_request.admin_note
                }
            }, status=status.HTTP_200_OK)

        except ValidationError as error:

            return Response({
                "message": "Product rejection failed.",
                "errors": error.messages
            }, status=status.HTTP_400_BAD_REQUEST)


class AdminCategoryCreateView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):

        serializer = AdminCategorySerializer(
            data=request.data
        )

        if serializer.is_valid():

            category = serializer.save()

            # Clear cached seller category tree
            cache.delete("seller:categories:tree")

            return Response({
                "message": "Category created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Category creation failed.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminCategoryUpdateView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):

        # Get the category
        category = get_object_or_404(
            Category,
            id=pk
        )

        # Validate incoming data
        serializer = AdminCategoryUpdateSerializer(
            category,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            return Response({
                "message": "Category update failed.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update category through service
        updated_category = update_category(
            category,
            serializer.validated_data
        )

        # Prepare updated category response
        response_serializer = AdminCategorySerializer(
            updated_category
        )

        return Response({
            "message": "Category updated successfully.",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)

class AdminProductTypeCreateView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):

        # Validate incoming data
        serializer = AdminProductTypeSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response({
                "message": "Product type creation failed.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create product type through service
        product_type = create_product_type(
            serializer.validated_data
        )

        # Serialize created product type
        response_serializer = AdminProductTypeSerializer(
            product_type
        )

        return Response({
            "message": "Product type created successfully.",
            "data": response_serializer.data
        }, status=status.HTTP_201_CREATED)



class AdminAttributeConfigurationView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):

        # Validate incoming data
        serializer = AdminAttributeConfigurationSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response({
                "message": "Attribute configuration failed.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get validated product type and attributes
        product_type = serializer.validated_data["product_type"]
        attributes_data = serializer.validated_data["attributes"]

        try:

            # Configure attributes through service
            configure_product_attributes(
                product_type,
                attributes_data
            )

            # Fetch updated mappings with their values
            mappings = ProductTypeAttribute.objects.filter(
                product_type=product_type
            ).select_related(
                "attribute"
            ).prefetch_related(
                "attribute__values"
            )

            # Prepare response
            response_serializer = AdminProductTypeAttributeResponseSerializer(
                mappings,
                many=True
            )

            return Response({
                "message": "Product attributes configured successfully.",
                "product_type": {
                    "id": product_type.id,
                    "name": product_type.name
                },
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)

        except ValidationError as error:

            return Response({
                "message": "Attribute configuration failed.",
                "errors": error.messages
            }, status=status.HTTP_400_BAD_REQUEST)