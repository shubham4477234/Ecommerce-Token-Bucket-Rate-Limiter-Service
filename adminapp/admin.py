from django.contrib import admin, messages
from django.core.cache import cache
from django.db import transaction

from mptt.admin import MPTTModelAdmin

from seller.models import (
    AttributeValue,
    Category,
    ProductTypeAttribute,
    ProductType,
    Attribute,
    ProductRequest,
    SellerProduct,
    ProductLineAttributeValue,
)

from config.cache_utils import (
    invalidate_customer_product_cache,
    invalidate_customer_product_detail_cache,
)

from .services import (
    approve_product_request,
    reject_product_request,
)


def invalidate_customer_listings(listing_ids):
    """
    Invalidate detail caches for affected seller listings
    and invalidate the general customer product listing cache.
    """

    for listing_id in set(listing_ids):
        invalidate_customer_product_detail_cache(listing_id)

    # Invalidate the general product listing cache
    invalidate_customer_product_cache()

@admin.register(ProductRequest)
class ProductRequestAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "seller",
        "category",
        "product_type",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "category",
        "product_type",
        "created_at",
    )

    search_fields = (
        "name",
        "seller__store_name",
        "seller__business_email",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "seller",
        "created_at",
        "updated_at",
    )

    list_select_related = (
        "seller",
        "category",
        "product_type",
    )

    actions = [
        "approve_selected_requests",
        "reject_selected_requests"
    ]

    @admin.action(description="Approve selected requests")
    def approve_selected_requests(self, request, queryset):

        for product_request in queryset:
            try:
                approve_product_request(product_request)

            except Exception as error:
                self.message_user(
                    request,
                    f"Request #{product_request.id}: {error}",
                    level=messages.ERROR
                )

        self.message_user(
            request,
            "Approval action completed.",
            level=messages.SUCCESS
        )

    @admin.action(description="Reject selected requests")
    def reject_selected_requests(self, request, queryset):

        for product_request in queryset:
            try:
                reject_product_request(
                    product_request,
                    "Rejected by admin through Django Admin."
                )

            except Exception as error:
                self.message_user(
                    request,
                    f"Request #{product_request.id}: {error}",
                    level=messages.ERROR
                )

        self.message_user(
            request,
            "Rejection action completed.",
            level=messages.SUCCESS
        )



@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):

    list_display = (
        "id",
        "name",
        "slug",
        "parent",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
    )

    ordering = (
        "tree_id",
        "lft",
    )

    list_select_related = (
        "parent",
    )

    fields = (
        "name",
        "slug",
        "parent",
        "is_active",
    )
    
    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        # Clear seller category cache
        cache.delete("seller:categories:tree")

        def invalidate_category_cache():

            # Get all seller listings associated with this category
            seller_product_ids = SellerProduct.objects.filter(
                product__category_id=obj.pk
            ).values_list(
                "id",
                flat=True
            )

            # Invalidate affected customer listing and detail caches
            for seller_product_id in seller_product_ids:
                invalidate_customer_product_detail_cache(
                    seller_product_id
                )

            # Invalidate overall customer product listing cache
            invalidate_customer_product_cache()

        # Execute invalidation after database transaction commits
        transaction.on_commit(invalidate_category_cache)

class ProductTypeAttributeInline(admin.TabularInline):
    model = ProductTypeAttribute
    extra = 1
    autocomplete_fields = ["attribute"]


class ProductTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "parent",
        "is_active",
    )

    list_filter = ("is_active",)

    search_fields = ("name",)

    ordering = ("name",)

    inlines = [
        ProductTypeAttributeInline,
    ]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        cache.delete(
            f"seller:product-type:{form.instance.id}:attributes"
        )


class AttributeValueInline(admin.TabularInline):

    model = AttributeValue
    extra = 1

class ProductTypeAttributeInline(admin.TabularInline):

    model = ProductTypeAttribute
    extra = 1

    autocomplete_fields = ["attribute"]


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    inlines = [
        AttributeValueInline,
    ]

    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        def invalidate_attribute_cache():

            # Find listings using this attribute
            listing_ids = ProductLineAttributeValue.objects.filter(
                attribute_value__attribute_id=obj.pk
            ).values_list(
                "product_line__seller_product_id",
                flat=True
            ).distinct()

            # Invalidate affected customer caches
            invalidate_customer_listings(listing_ids)

            # Find related product types
            product_type_ids = ProductTypeAttribute.objects.filter(
                attribute_id=obj.pk
            ).values_list(
                "product_type_id",
                flat=True
            )

            # Clear seller attribute caches
            for product_type_id in product_type_ids:
                cache.delete(
                    f"seller:product-type:{product_type_id}:attributes"
                )

        transaction.on_commit(invalidate_attribute_cache)

    def save_related(self, request, form, formsets, change):

        super().save_related(request, form, formsets, change)

        def invalidate_related_attribute_cache():

            # Find product types using this attribute
            product_type_ids = ProductTypeAttribute.objects.filter(
                attribute=form.instance
            ).values_list(
                "product_type_id",
                flat=True
            )

            for product_type_id in product_type_ids:
                cache.delete(
                    f"seller:product-type:{product_type_id}:attributes"
                )

            # Find customer listings using this attribute
            listing_ids = ProductLineAttributeValue.objects.filter(
                attribute_value__attribute_id=form.instance.id
            ).values_list(
                "product_line__seller_product_id",
                flat=True
            ).distinct()

            invalidate_customer_listings(listing_ids)

        transaction.on_commit(invalidate_related_attribute_cache)



class ProductTypeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "parent",
        "is_active",
    )

    list_filter = ("is_active",)

    search_fields = ("name",)

    ordering = ("name",)

    inlines = [
        ProductTypeAttributeInline,
    ]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        cache.delete(
            f"seller:product-type:{form.instance.id}:attributes"
        )