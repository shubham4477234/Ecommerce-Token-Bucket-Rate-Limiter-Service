from django.conf import settings
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

class SellerProfile(models.Model):

    VERIFICATION_STATUS = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="seller_profile"
    )

    store_name = models.CharField(max_length=150)

    store_slug = models.SlugField(
        max_length=180,
        unique=True
    )

    description = models.TextField(blank=True)

    gst_number = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True
    )

    business_email = models.EmailField()

    business_phone = models.CharField(max_length=15)

    address = models.TextField()

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default="pending"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "seller_profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return self.store_name




class IsActiveQueryset(models.QuerySet):

    def is_active(self):
        return self.filter(is_active=True)


class Category(MPTTModel):

    name = models.CharField(
        max_length=235,
        unique=True
    )

    slug = models.SlugField(
        max_length=255,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=False
    )

    parent = TreeForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children"
    )

    objects = IsActiveQueryset.as_manager()

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        db_table = "seller_categories"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class ProductType(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "seller_product_types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Attribute(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "seller_attributes"
        ordering = ["name"]

    def __str__(self):
        return self.name



class AttributeValue(models.Model):

    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name="values"
    )

    value = models.CharField(
        max_length=100
    )

    class Meta:
        db_table = "seller_attribute_values"
        ordering = ["value"]

        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "value"],
                name="unique_value_per_attribute"
            )
        ]

    def __str__(self):
        return f"{self.attribute.name} - {self.value}"



class ProductTypeAttribute(models.Model):

    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.CASCADE,
        related_name="type_attributes"
    )

    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name="product_types"
    )

    is_required = models.BooleanField(default=False)

    class Meta:
        db_table = "seller_product_type_attributes"

        constraints = [
            models.UniqueConstraint(
                fields=["product_type", "attribute"],
                name="unique_attribute_per_product_type"
            )
        ]

    def __str__(self):
        return f"{self.product_type.name} - {self.attribute.name}"


class Product(models.Model):

    name = models.CharField(
        max_length=200
    )

    slug = models.SlugField(
        max_length=220,
        unique=True
    )

    pid = models.CharField(
        max_length=30,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    is_digital = models.BooleanField(
        default=False
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.PROTECT,
        related_name="products"
    )

    is_active = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "seller_products"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["category", "is_active"],
                name="seller_prod_cat_active_idx"
            ),
            models.Index(
                fields=["product_type", "is_active"],
                name="seller_prod_type_active_idx"
            ),
        ]

    def __str__(self):
        return self.name



class SellerProduct(models.Model):

    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.PROTECT,
        related_name="products"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="seller_listings"
    )

    seller_product_name = models.CharField(
        max_length=200,
        blank=True
    )

    is_active = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "seller_listings"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["seller", "product"],
                name="unique_product_per_seller"
            )
        ]

    def __str__(self):
        return f"{self.seller.store_name} - {self.product.name}"



class ProductAttributeValue(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="attribute_values"
    )

    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name="product_assignments"
    )

    class Meta:
        db_table = "seller_product_attribute_values"

        constraints = [
            models.UniqueConstraint(
                fields=["product", "attribute_value"],
                name="unique_product_attribute_value"
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.attribute_value}"


from django.core.validators import MinValueValidator
from django.db import models


class ProductLine(models.Model):

    seller_product = models.ForeignKey(
        SellerProduct,
        on_delete=models.PROTECT,
        related_name="product_lines"
    )

    sku = models.CharField(
        max_length=100,
        unique=True
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    stock_qty = models.PositiveIntegerField(
        default=0
    )

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "seller_product_lines"
        ordering = ["id"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="product_line_price_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(stock_qty__gte=0),
                name="product_line_stock_nonnegative"
            ),
        ]

        indexes = [
            models.Index(
                fields=["seller_product", "is_active"],
                name="seller_line_active_idx"
            )
        ]

    def __str__(self):
        return self.sku


from django.core.exceptions import ValidationError


class ProductLineAttributeValue(models.Model):

    product_line = models.ForeignKey(
        ProductLine,
        on_delete=models.CASCADE,
        related_name="attribute_values"
    )

    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.PROTECT,
        related_name="product_line_assignments"
    )

    class Meta:
        db_table = "seller_product_line_attribute_values"

        constraints = [
            models.UniqueConstraint(
                fields=["product_line", "attribute_value"],
                name="unique_value_per_product_line"
            )
        ]

    def clean(self):

        if not self.product_line_id or not self.attribute_value_id:
            return

        product_type_id = (
            self.product_line.seller_product.product.product_type_id
        )

        attribute_id = self.attribute_value.attribute_id

        # Check whether this attribute is allowed
        # for the product's ProductType.

        is_allowed = ProductTypeAttribute.objects.filter(
            product_type_id=product_type_id,
            attribute_id=attribute_id
        ).exists()

        if not is_allowed:
            raise ValidationError(
                "This attribute is not allowed for this product type."
            )

        # Prevent assigning two values to the same
        # attribute on one product variant.

        duplicate = ProductLineAttributeValue.objects.filter(
            product_line_id=self.product_line_id,
            attribute_value__attribute_id=attribute_id
        ).exclude(pk=self.pk).exists()

        if duplicate:
            raise ValidationError(
                "This product variant already has a value for this attribute."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_line.sku} - {self.attribute_value}"



class ProductImage(models.Model):

    seller_product = models.ForeignKey(
        SellerProduct,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="seller/products/%Y/%m/"
    )

    alternative_text = models.CharField(
        max_length=150,
        blank=True
    )

    is_primary = models.BooleanField(
        default=False
    )

    display_order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "seller_product_images"

        ordering = ["display_order", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["seller_product"],
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_listing"
            )
        ]

    def __str__(self):
        return f"{self.seller_product.product.name} - Image"
