from django.contrib import admin, messages
from django.contrib import admin
from django.core.cache import cache
from mptt.admin import MPTTModelAdmin

from seller.models import AttributeValue, Category, ProductTypeAttribute, ProductType, Attribute, ProductRequest
from seller.models import ProductRequest, ProductType
from .services import (
    approve_product_request,
    reject_product_request
)


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
        "is_active"
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    inlines = [
        AttributeValueInline
    ]

    def save_related(self, request, form, formsets, change):

        super().save_related(request, form, formsets, change)

        # Find product types using this attribute
        product_type_ids = ProductTypeAttribute.objects.filter(
            attribute=form.instance
        ).values_list(
            "product_type_id",
            flat=True
        )

        # Clear their attribute caches
        for product_type_id in product_type_ids:

            cache.delete(
                f"seller:product-type:{product_type_id}:attributes"
            )

@admin.register(ProductType)
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