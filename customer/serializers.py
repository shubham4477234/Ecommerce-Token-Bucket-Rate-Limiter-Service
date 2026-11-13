
from rest_framework import serializers

from seller.models import (
    SellerProduct,
    ProductLine,
    ProductImage,
    ProductLineAttributeValue,
)


class ProductLineAttributeSerializer(serializers.ModelSerializer):
    attribute = serializers.CharField(
        source="attribute_value.attribute.name",
        read_only=True
    )

    value = serializers.CharField(
        source="attribute_value.value",
        read_only=True
    )

    class Meta:
        model = ProductLineAttributeValue
        fields = ["attribute", "value"]


class ProductLineSerializer(serializers.ModelSerializer):
    attributes = ProductLineAttributeSerializer(
        source="attribute_values",
        many=True,
        read_only=True
    )

    class Meta:
        model = ProductLine
        fields = [
            "id",
            "sku",
            "price",
            "stock_qty",
            "attributes",
        ]


class ProductImageSerializer(serializers.ModelSerializer):

    image = serializers.ImageField(read_only=True)

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "image",
            "alternative_text",
            "is_primary",
            "display_order",
        ]


class CustomerProductListSerializer(serializers.ModelSerializer):

    product_id = serializers.IntegerField(
        source="product.id",
        read_only=True
    )

    product_name = serializers.SerializerMethodField()

    slug = serializers.CharField(
        source="product.slug",
        read_only=True
    )

    description = serializers.CharField(
        source="product.description",
        read_only=True
    )

    category = serializers.CharField(
        source="product.category.name",
        read_only=True
    )

    product_type = serializers.CharField(
        source="product.product_type.name",
        read_only=True
    )

    seller_name = serializers.CharField(
        source="seller.store_name",
        read_only=True
    )

    images = ProductImageSerializer(
        many=True,
        read_only=True
    )

    variants = ProductLineSerializer(
        source="available_product_lines",
        many=True,
        read_only=True
    )

    def get_product_name(self, obj):
        return obj.seller_product_name or obj.product.name

    class Meta:
        model = SellerProduct
        fields = [
            "id",
            "product_id",
            "product_name",
            "slug",
            "description",
            "category",
            "product_type",
            "seller_name",
            "images",
            "variants",
        ]



class CustomerProductDetailSerializer(serializers.ModelSerializer):

    product_id = serializers.IntegerField(
        source="product.id",
        read_only=True
    )

    product_name = serializers.SerializerMethodField()

    slug = serializers.CharField(
        source="product.slug",
        read_only=True
    )

    pid = serializers.CharField(
        source="product.pid",
        read_only=True
    )

    description = serializers.CharField(
        source="product.description",
        read_only=True
    )

    category = serializers.CharField(
        source="product.category.name",
        read_only=True
    )

    product_type = serializers.CharField(
        source="product.product_type.name",
        read_only=True
    )

    seller_name = serializers.CharField(
        source="seller.store_name",
        read_only=True
    )

    seller_description = serializers.CharField(
        source="seller.description",
        read_only=True
    )

    images = ProductImageSerializer(
        many=True,
        read_only=True
    )

    variants = ProductLineSerializer(
        source="detail_product_lines",
        many=True,
        read_only=True
    )

    def get_product_name(self, obj):
        return obj.seller_product_name or obj.product.name

    class Meta:
        model = SellerProduct
        fields = [
            "id",
            "product_id",
            "product_name",
            "slug",
            "pid",
            "description",
            "category",
            "product_type",
            "seller_name",
            "seller_description",
            "images",
            "variants",
            "created_at",
        ]
