from django.db import models
from django.conf import settings
from seller.models import ProductLine


class Cart(models.Model):

    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.customer}"


class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product_line = models.ForeignKey(
        ProductLine,
        on_delete=models.PROTECT,
        related_name="cart_items"
    )

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product_line"],
                name="unique_product_line_per_cart"
            )
        ]

    def __str__(self):
        return f"{self.product_line} x {self.quantity}"