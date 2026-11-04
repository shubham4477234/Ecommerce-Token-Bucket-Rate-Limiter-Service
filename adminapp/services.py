import uuid
from django.core.cache import cache

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from seller.models import Product, ProductRequest, Category, ProductType, ProductTypeAttribute, Attribute, AttributeValue


@transaction.atomic
def approve_product_request(product_request):

    # Only pending requests can be approved
    if product_request.status != "pending":
        raise ValidationError(
            "This product request has already been processed."
        )

    # Check whether category and product type are still active
    if not product_request.category.is_active:
        raise ValidationError("This category is inactive.")

    if not product_request.product_type.is_active:
        raise ValidationError("This product type is inactive.")

    # Prevent duplicate products
    if Product.objects.filter(
        name__iexact=product_request.name
    ).exists():
        raise ValidationError(
            "A product with this name already exists."
        )

    # Generate unique slug and product ID
    unique_code = uuid.uuid4().hex[:10].upper()

    product_slug = f"{slugify(product_request.name)}-{unique_code.lower()}"
    product_pid = f"PRD-{unique_code}"

    # Create product in the shared catalogue
    product = Product.objects.create(
        name=product_request.name,
        slug=product_slug,
        pid=product_pid,
        description=product_request.description,
        category=product_request.category,
        product_type=product_request.product_type,
        is_digital=False,
        is_active=True
    )

    # Update the original request
    product_request.status = "approved"

    product_request.save(
        update_fields=["status", "updated_at"]
    )

    return product


@transaction.atomic
def reject_product_request(product_request, admin_note):

    # Only pending requests can be rejected
    if product_request.status != "pending":
        raise ValidationError(
            "This product request has already been processed."
        )

    # Save rejection status and reason
    product_request.status = "rejected"
    product_request.admin_note = admin_note

    product_request.save(
        update_fields=["status", "admin_note", "updated_at"]
    )

    return product_request

@transaction.atomic
def update_category(category, validated_data):

    # Check whether category name is changing
    new_name = validated_data.get("name")

    if new_name and new_name != category.name:

        # Generate a new slug
        base_slug = slugify(new_name)
        slug = base_slug
        counter = 1

        # Ensure slug is unique, excluding current category
        while Category.objects.filter(
            slug=slug
        ).exclude(id=category.id).exists():

            counter += 1
            slug = f"{base_slug}-{counter}"

        category.name = new_name
        category.slug = slug

    # Update parent if supplied
    if "parent" in validated_data:
        category.parent = validated_data["parent"]

    # Update active status if supplied
    if "is_active" in validated_data:
        category.is_active = validated_data["is_active"]

    # Save changes
    category.save()

    # Clear seller category cache
    cache.delete("seller:categories:tree")

    return category

@transaction.atomic
def update_category(category, validated_data):

    # Check whether category name is changing
    new_name = validated_data.get("name")

    if new_name and new_name != category.name:

        # Generate a new slug
        base_slug = slugify(new_name)
        slug = base_slug
        counter = 1

        # Ensure slug is unique, excluding current category
        while Category.objects.filter(
            slug=slug
        ).exclude(id=category.id).exists():

            counter += 1
            slug = f"{base_slug}-{counter}"

        category.name = new_name
        category.slug = slug

    # Update parent if supplied
    if "parent" in validated_data:
        category.parent = validated_data["parent"]

    # Update active status if supplied
    if "is_active" in validated_data:
        category.is_active = validated_data["is_active"]

    # Save changes
    category.save()

    # Clear seller category cache
    cache.delete("seller:categories:tree")

    return category

@transaction.atomic
def create_product_type(validated_data):

    return ProductType.objects.create(**validated_data)



@transaction.atomic
def configure_product_attributes(product_type, attributes_data):

    configured_mappings = []

    for item in attributes_data:

        # Find existing attribute or create a new one
        attribute = Attribute.objects.filter(
            name__iexact=item["name"]
        ).first()

        if not attribute:
            attribute = Attribute.objects.create(
                name=item["name"],
                is_active=True
            )

        # Do not configure an inactive attribute
        if not attribute.is_active:
            raise ValidationError(
                f"Attribute '{attribute.name}' is inactive."
            )

        # Create missing attribute values
        for value in item["values"]:

            existing_value = AttributeValue.objects.filter(
                attribute=attribute,
                value__iexact=value
            ).first()

            if not existing_value:
                AttributeValue.objects.create(
                    attribute=attribute,
                    value=value
                )

        # Create mapping or get existing mapping
        mapping, mapping_created = ProductTypeAttribute.objects.get_or_create(
            product_type=product_type,
            attribute=attribute,
            defaults={
                "is_required": item["is_required"]
            }
        )

        # Update required status if mapping already exists
        if not mapping_created:
            mapping.is_required = item["is_required"]
            mapping.save(update_fields=["is_required"])

        configured_mappings.append(mapping)

    # Invalidate Seller API 6 cache
    cache.delete(
        f"seller:product-type:{product_type.id}:attributes"
    )

    return configured_mappings