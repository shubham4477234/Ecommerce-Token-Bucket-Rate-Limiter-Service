from rest_framework import serializers
from seller.models import ProductRequest, Category, ProductType, ProductTypeAttribute, Attribute, AttributeValue
from rest_framework import serializers
from django.utils.text import slugify


class AdminProductRequestSerializer(serializers.ModelSerializer):

    seller_name = serializers.CharField(
        source="seller.store_name",
        read_only=True
    )

    seller_email = serializers.CharField(
        source="seller.business_email",
        read_only=True
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    product_type_name = serializers.CharField(
        source="product_type.name",
        read_only=True
    )

    class Meta:
        model = ProductRequest

        fields = [
            "id",
            "name",
            "description",
            "seller",
            "seller_name",
            "seller_email",
            "category",
            "category_name",
            "product_type",
            "product_type_name",
            "status",
            "admin_note",
            "created_at",
            "updated_at"
        ]


class AdminCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category

        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "is_active",
        ]

        read_only_fields = ["id", "slug"]

    def validate_parent(self, value):

        if value and not value.is_active:
            raise serializers.ValidationError(
                "Cannot select an inactive parent category."
            )

        return value

    def create(self, validated_data):

        # Generate slug from category name
        base_slug = slugify(validated_data["name"])
        slug = base_slug
        counter = 1

        # Ensure slug is unique
        while Category.objects.filter(slug=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"

        validated_data["slug"] = slug

        return Category.objects.create(**validated_data)


class AdminCategoryUpdateSerializer(serializers.Serializer):

    name = serializers.CharField(
        max_length=255,
        required=False
    )

    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )

    is_active = serializers.BooleanField(
        required=False
    )

    def validate_parent(self, parent):

        category = self.instance

        if parent is None:
            return parent

        # A category cannot be its own parent
        if parent.id == category.id:
            raise serializers.ValidationError(
                "A category cannot be its own parent."
            )

        # A category cannot be moved under its own child
        descendant_ids = category.get_descendants().values_list(
            "id",
            flat=True
        )

        if parent.id in descendant_ids:
            raise serializers.ValidationError(
                "A category cannot be moved under its own subcategory."
            )

        return parent


class AdminProductTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductType

        fields = [
            "id",
            "name",
            "parent",
            "is_active"
        ]

        read_only_fields = ["id"]

    def validate_parent(self, parent):

        if parent and not parent.is_active:
            raise serializers.ValidationError(
                "Cannot select an inactive parent product type."
            )

        return parent


class AdminAttributeConfigItemSerializer(serializers.Serializer):

    name = serializers.CharField(
        required=True,
        trim_whitespace=True
    )

    values = serializers.ListField(
        child=serializers.CharField(
            trim_whitespace=True
        ),
        allow_empty=False
    )

    is_required = serializers.BooleanField(
        required=True
    )

    def validate_name(self, value):

        if not value:
            raise serializers.ValidationError(
                "Attribute name cannot be empty."
            )

        return value

    def validate_values(self, values):

        if any(not value for value in values):
            raise serializers.ValidationError(
                "Attribute values cannot be empty."
            )

        normalized_values = [value.casefold() for value in values]

        if len(normalized_values) != len(set(normalized_values)):
            raise serializers.ValidationError(
                "Duplicate values are not allowed."
            )

        return values


class AdminAttributeConfigurationSerializer(serializers.Serializer):

    product_type = serializers.PrimaryKeyRelatedField(
        queryset=ProductType.objects.filter(is_active=True)
    )

    attributes = AdminAttributeConfigItemSerializer(
        many=True,
        allow_empty=False
    )

    def validate_attributes(self, attributes):

        names = [item["name"].casefold() for item in attributes]

        if len(names) != len(set(names)):
            raise serializers.ValidationError(
                "Duplicate attributes are not allowed in the same request."
            )

        return attributes


class AdminAttributeValueResponseSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttributeValue
        fields = ["id", "value"]


class AdminAttributeResponseSerializer(serializers.ModelSerializer):

    values = AdminAttributeValueResponseSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Attribute
        fields = ["id", "name", "values"]


class AdminProductTypeAttributeResponseSerializer(
    serializers.ModelSerializer
):

    attribute = AdminAttributeResponseSerializer(read_only=True)

    class Meta:
        model = ProductTypeAttribute
        fields = ["id", "attribute", "is_required"]