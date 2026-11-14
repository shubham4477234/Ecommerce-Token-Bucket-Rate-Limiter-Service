
from rest_framework import serializers

from seller.models import (
    SellerProduct,
    ProductLine,
    ProductImage,
    ProductLineAttributeValue,Category
)
from customer.models import Cart, CartItem

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


class CustomerCategorySerializer(serializers.ModelSerializer):

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "children",
        ]

    def get_children(self, obj):

        # Get only active subcategories
        active_children = [
            child
            for child in obj.get_children()
            if child.is_active
        ]

        # Serialize the children using the same serializer
        return CustomerCategorySerializer(
            active_children,
            many=True,
            context=self.context
        ).data



class CartItemSerializer(serializers.ModelSerializer):

    product_line_id = serializers.IntegerField(
        source="product_line.id",
        read_only=True
    )

    product_name = serializers.CharField(
        source="product_line.seller_product.product.name",
        read_only=True
    )

    seller_name = serializers.CharField(
        source="product_line.seller_product.seller.store_name",
        read_only=True
    )

    sku = serializers.CharField(
        source="product_line.sku",
        read_only=True
    )

    price = serializers.DecimalField(
        source="product_line.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    stock_available = serializers.IntegerField(
        source="product_line.stock_qty",
        read_only=True
    )

    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_line_id",
            "product_name",
            "seller_name",
            "sku",
            "price",
            "quantity",
            "subtotal",
            "stock_available",
        ]

    def get_subtotal(self, obj):
        return obj.product_line.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(many=True, read_only=True)

    total_items = serializers.SerializerMethodField()

    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "total_amount",
        ]

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_total_amount(self, obj):
        total = sum(
            item.product_line.price * item.quantity
            for item in obj.items.all()
        )

        return total