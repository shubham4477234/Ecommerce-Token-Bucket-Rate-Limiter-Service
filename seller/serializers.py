from rest_framework import serializers
from django.db import transaction
from .models import (
    SellerProfile,
    Category,
    ProductRequest,
    ProductType,
    Attribute,
    AttributeValue,
    ProductTypeAttribute, 
    Product, 
    SellerProduct,ProductLine,
    ProductLineAttributeValue,
    AttributeValue,
    ProductTypeAttribute,
    ProductImage
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


class SellerProductUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SellerProduct

        fields = [
            "id",
            "seller_product_name",
            "is_active",
            "updated_at",
        ]

        read_only_fields = ["id", "updated_at"]



class ProductVariantCreateSerializer(serializers.ModelSerializer):

    attributes = serializers.PrimaryKeyRelatedField(
        queryset=AttributeValue.objects.select_related("attribute").filter(
            attribute__is_active=True
        ),
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = ProductLine

        fields = [
            "id",
            "sku",
            "price",
            "stock_qty",
            "weight",
            "attributes",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "is_active",
            "created_at",
        ]

    def validate(self, data):

        # Get the seller's product listing
        seller_product = self.context["seller_product"]

        # Get the product type of this catalogue product
        product_type = seller_product.product.product_type

        # Get attributes allowed for this product type
        mappings = ProductTypeAttribute.objects.filter(
            product_type=product_type,
            attribute__is_active=True
        )

        # Get all allowed attribute IDs
        allowed_attribute_ids = set(
            mappings.values_list("attribute_id", flat=True)
        )

        # Get the selected attribute values
        selected_values = data.get("attributes", [])

        selected_attribute_ids = []

        for value in selected_values:

            attribute_id = value.attribute_id

            # Check whether this attribute is allowed
            if attribute_id not in allowed_attribute_ids:
                raise serializers.ValidationError({
                    "attributes": (
                        f"{value.attribute.name} is not allowed "
                        "for this product type."
                    )
                })

            selected_attribute_ids.append(attribute_id)

        # Prevent selecting multiple values for the same attribute
        if len(selected_attribute_ids) != len(set(selected_attribute_ids)):
            raise serializers.ValidationError({
                "attributes": "Select only one value for each attribute."
            })

        # Check required attributes
        required_attribute_ids = set(
            mappings.filter(is_required=True).values_list(
                "attribute_id",
                flat=True
            )
        )

        missing_attributes = required_attribute_ids - set(
            selected_attribute_ids
        )

        if missing_attributes:
            raise serializers.ValidationError({
                "attributes": "Please provide all required product attributes."
            })

        return data

    def create(self, validated_data):

        # Remove attributes from normal ProductLine fields
        selected_values = validated_data.pop("attributes", [])

        # Create the product variant
        product_line = ProductLine.objects.create(
            seller_product=self.context["seller_product"],
            **validated_data
        )

        # Save selected attribute values
        for value in selected_values:
            ProductLineAttributeValue.objects.create(
                product_line=product_line,
                attribute_value=value
            )

        return product_line


class VariantAttributeListSerializer(serializers.ModelSerializer):

    attribute_name = serializers.CharField(
        source="attribute_value.attribute.name",
        read_only=True
    )

    value = serializers.CharField(
        source="attribute_value.value",
        read_only=True
    )

    class Meta:
        model = ProductLineAttributeValue

        fields = [
            "id",
            "attribute_name",
            "value",
        ]


class ProductVariantListSerializer(serializers.ModelSerializer):

    attributes = serializers.SerializerMethodField()

    class Meta:
        model = ProductLine

        fields = [
            "id",
            "sku",
            "price",
            "stock_qty",
            "weight",
            "attributes",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_attributes(self, obj):

        # Get the attribute values belonging to this variant
        attribute_values = ProductLineAttributeValue.objects.filter(
            product_line=obj
        ).select_related(
            "attribute_value__attribute"
        )

        return VariantAttributeListSerializer(
            attribute_values,
            many=True
        ).data


class ProductVariantUpdateSerializer(serializers.ModelSerializer):

    attributes = serializers.PrimaryKeyRelatedField(
        queryset=AttributeValue.objects.select_related("attribute").filter(
            attribute__is_active=True
        ),
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = ProductLine

        fields = [
            "id",
            "sku",
            "price",
            "stock_qty",
            "weight",
            "attributes",
            "is_active",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "updated_at",
        ]

    def validate(self, data):

        # Validate attributes only when the seller sends them
        if "attributes" not in data:
            return data

        product_type = self.instance.seller_product.product.product_type

        # Get attributes allowed for this product type
        mappings = ProductTypeAttribute.objects.filter(
            product_type=product_type,
            attribute__is_active=True
        )

        allowed_attribute_ids = set(
            mappings.values_list("attribute_id", flat=True)
        )

        selected_values = data["attributes"]
        selected_attribute_ids = []

        for value in selected_values:

            attribute_id = value.attribute_id

            if attribute_id not in allowed_attribute_ids:
                raise serializers.ValidationError({
                    "attributes": (
                        f"{value.attribute.name} is not allowed "
                        "for this product type."
                    )
                })

            selected_attribute_ids.append(attribute_id)

        # Prevent multiple values for the same attribute
        if len(selected_attribute_ids) != len(set(selected_attribute_ids)):
            raise serializers.ValidationError({
                "attributes": "Select only one value for each attribute."
            })

        # Check required attributes
        required_attribute_ids = set(
            mappings.filter(is_required=True).values_list(
                "attribute_id",
                flat=True
            )
        )

        missing_attributes = required_attribute_ids - set(
            selected_attribute_ids
        )

        if missing_attributes:
            raise serializers.ValidationError({
                "attributes": "Please provide all required product attributes."
            })

        return data

    @transaction.atomic
    def update(self, instance, validated_data):

        # Get attributes if they were included in the request
        selected_values = validated_data.pop("attributes", None)

        # Update normal variant fields
        instance = super().update(instance, validated_data)

        # Replace existing attributes only if new ones were provided
        if selected_values is not None:

            ProductLineAttributeValue.objects.filter(
                product_line=instance
            ).delete()

            for value in selected_values:
                ProductLineAttributeValue.objects.create(
                    product_line=instance,
                    attribute_value=value
                )

        return instance

class ProductImageUploadSerializer(serializers.Serializer):

    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
        write_only=True
    )

    primary_image_index = serializers.IntegerField(
        required=False,
        min_value=0
    )

    def validate(self, data):

        images = data["images"]
        primary_index = data.get("primary_image_index")

        # Check whether the selected primary image exists
        if primary_index is not None and primary_index >= len(images):
            raise serializers.ValidationError({
                "primary_image_index": "Invalid image selection."
            })

        return data

    @transaction.atomic
    def create(self, validated_data):

        seller_product = self.context["seller_product"]

        images = validated_data["images"]
        primary_index = validated_data.get("primary_image_index")

        created_images = []

        # Find the next display order
        last_order = ProductImage.objects.filter(
            seller_product=seller_product
        ).order_by("-display_order").values_list(
            "display_order",
            flat=True
        ).first()

        next_order = (last_order + 1) if last_order is not None else 1

        # If no primary image exists, make the first uploaded image primary
        has_primary = ProductImage.objects.filter(
            seller_product=seller_product,
            is_primary=True
        ).exists()

        if primary_index is None and not has_primary:
            primary_index = 0

        # If seller selected a new primary image, remove old primary status
        if primary_index is not None:
            ProductImage.objects.filter(
                seller_product=seller_product,
                is_primary=True
            ).update(is_primary=False)

        # Save all uploaded images
        for index, image in enumerate(images):

            product_image = ProductImage.objects.create(
                seller_product=seller_product,
                image=image,
                is_primary=(index == primary_index),
                display_order=next_order + index
            )

            created_images.append(product_image)

        return created_images


class ProductImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "created_at",
        ]