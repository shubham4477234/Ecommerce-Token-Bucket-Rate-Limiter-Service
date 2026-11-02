from rest_framework import serializers
from .models import (
    SellerProfile,
    Category,
    ProductRequest,
    ProductType,
    Attribute,
    AttributeValue,
    ProductTypeAttribute, Product, SellerProduct
)


class SellerProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = SellerProfile

        fields = [
            "id",
            "store_name",
            "store_slug",
            "description",
            "gst_number",
            "business_email",
            "business_phone",
            "address",
            "verification_status",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "verification_status",
            "is_active",
            "created_at",
            "updated_at",
        ]



class CategorySerializer(serializers.ModelSerializer):

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "children"
        ]

    def get_children(self, category):
        # Get active subcategories of this category
        subcategories = category.get_children().filter(is_active=True)

        # Convert subcategories into JSON
        return CategorySerializer(
            subcategories,
            many=True
        ).data


class ProductTypeSerializer(serializers.ModelSerializer):

  class Meta:
      model = ProductType
      fields = [
            "id",
            "name",
            "parent"
        ]


class AttributeValueSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttributeValue
        fields = ["id", "value"]


class AttributeSerializer(serializers.ModelSerializer):

    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = Attribute
        fields = ["id", "name", "values"]


class ProductTypeAttributeSerializer(serializers.ModelSerializer):

    attribute = AttributeSerializer(read_only=True)

    class Meta:
        model = ProductTypeAttribute
        fields = ["attribute", "is_required"]


class ProductSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    product_type_name = serializers.CharField(
        source="product_type.name",
        read_only=True
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "slug",
            "pid",
            "description",
            "is_digital",
            "category",
            "category_name",
            "product_type",
            "product_type_name",
        ]

class ProductRequestSerializer(serializers.ModelSerializer):

    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True)
    )

    product_type = serializers.PrimaryKeyRelatedField(
        queryset=ProductType.objects.filter(is_active=True)
    )

    class Meta:
        model = ProductRequest

        fields = [
            "id",
            "name",
            "description",
            "category",
            "product_type",
            "status",
            "admin_note",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "admin_note",
            "created_at",
        ]

    def validate(self, data):

        name = data["name"]
        category = data["category"]
        product_type = data["product_type"]

        # Check whether this product already exists
        if Product.objects.filter(
            name__iexact=name,
            category=category,
            product_type=product_type
        ).exists():

            raise serializers.ValidationError(
                "This product already exists. Please search the catalogue."
            )

        # Check whether someone has already requested this product
        if ProductRequest.objects.filter(
            name__iexact=name,
            category=category,
            product_type=product_type,
            status="pending"
        ).exists():

            raise serializers.ValidationError(
                "A request for this product is already pending."
            )

        return data

class AddProductToStoreSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )

    class Meta:
        model = SellerProduct

        fields = [
            "id",
            "product",
            "product_name",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "product_name",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate_product(self, value):

        seller = self.context["seller"]

        # Check whether this seller has already added this product
        if SellerProduct.objects.filter(
            seller=seller,
            product=value
        ).exists():

            raise serializers.ValidationError(
                "You have already added this product to your store."
            )

        return value
  

class SellerProductListSerializer(serializers.ModelSerializer):

    product_id = serializers.IntegerField(
        source="product.id",
        read_only=True
    )

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    category_name = serializers.CharField(
        source="product.category.name",
        read_only=True
    )

    product_type_name = serializers.CharField(
        source="product.product_type.name",
        read_only=True
    )

    class Meta:
        model = SellerProduct

        fields = [
            "id",
            "product_id",
            "product_name",
            "category_name",
            "product_type_name",
            "is_active",
            "created_at",
            "updated_at",
        ]