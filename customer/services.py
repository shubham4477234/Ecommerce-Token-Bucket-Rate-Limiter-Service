
from seller.models import ProductLine
from rest_framework.exceptions import ValidationError
from django.db import transaction
from customer.models import Cart, CartItem
from config.cache_utils import invalidate_customer_cart_cache

# Name of the guest cart inside Django session
GUEST_CART_SESSION_KEY = "guest_cart"


def add_to_guest_cart(request, product_line_id, quantity=1):

    # 1. Check whether the customer is already logged in
    if request.user.is_authenticated:
        raise ValidationError(
            "Logged-in customers should use the database cart."
        )

    # 2. Validate quantity
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
        raise ValidationError(
            {"quantity": "Quantity must be a positive integer."}
        )

    # 3. Find the selected product variant
    try:
        product_line = ProductLine.objects.select_related(
            "seller_product__product",
            "seller_product__seller"
        ).get(
            id=product_line_id,
            is_active=True,
            seller_product__is_active=True,
            seller_product__product__is_active=True,
            seller_product__seller__is_active=True,
            seller_product__seller__verification_status="verified"
        )

    except ProductLine.DoesNotExist:
        raise ValidationError(
            "This product variant is not available."
        )

    # 4. Check available stock
    if product_line.stock_qty <= 0:
        raise ValidationError(
            "This product is out of stock."
        )

    # 5. Get the existing guest cart from the session
    guest_cart = request.session.get(
        GUEST_CART_SESSION_KEY,
        {}
    )

    # 6. Get the current quantity of this product
    current_quantity = guest_cart.get(
        str(product_line_id),
        0
    )

    # 7. Calculate the new quantity
    new_quantity = current_quantity + quantity

    # 8. Check whether requested quantity exceeds stock
    if new_quantity > product_line.stock_qty:
        raise ValidationError(
            {
                "quantity": (
                    f"Only {product_line.stock_qty} units are available."
                )
            }
        )

    # 9. Update the guest cart
    guest_cart[str(product_line_id)] = new_quantity

    # 10. Save the updated cart in Django session
    request.session[GUEST_CART_SESSION_KEY] = guest_cart
    request.session.modified = True

    # 11. Return the updated cart
    return guest_cart



from django.db import transaction
from customer.models import Cart, CartItem
from config.cache_utils import invalidate_customer_cart_cache


def merge_guest_cart(request, user):

    # 1. Get guest cart from Django session
    guest_cart = request.session.get(
        GUEST_CART_SESSION_KEY,
        {}
    )

    # Nothing to merge
    if not guest_cart:
        return {
            "message": "No guest cart found.",
            "merged_items": 0,
            "skipped_items": 0
        }

    merged_items = 0
    skipped_items = 0

    # 2. Start database transaction
    with transaction.atomic():

        # 3. Get or create the customer's permanent cart
        cart, created = Cart.objects.get_or_create(
            customer=user
        )

        # 4. Process every guest cart item
        for product_line_id, guest_quantity in guest_cart.items():

            # Validate session quantity
            if (
                isinstance(guest_quantity, bool)
                or not isinstance(guest_quantity, int)
                or guest_quantity <= 0
            ):
                skipped_items += 1
                continue

            # 5. Find and lock the product variant
            product_line = ProductLine.objects.select_for_update().filter(
                id=product_line_id,
                is_active=True,
                seller_product__is_active=True,
                seller_product__product__is_active=True,
                seller_product__product__category__is_active=True,
                seller_product__product__product_type__is_active=True,
                seller_product__seller__is_active=True,
                seller_product__seller__verification_status="verified"
            ).first()

            # Product is no longer available
            if not product_line or product_line.stock_qty <= 0:
                skipped_items += 1
                continue

            # 6. Find existing item in customer's cart
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product_line=product_line,
                defaults={
                    "quantity": 0
                }
            )

            # 7. Calculate combined quantity
            new_quantity = cart_item.quantity + guest_quantity

            # 8. Don't exceed available stock
            new_quantity = min(
                new_quantity,
                product_line.stock_qty
            )

            # 9. Save the updated quantity
            if new_quantity > 0:
                cart_item.quantity = new_quantity
                cart_item.save(update_fields=["quantity", "updated_at"])

                merged_items += 1

    # 10. Clear guest cart only after successful transaction
    del request.session[GUEST_CART_SESSION_KEY]
    request.session.modified = True

    # 11. Invalidate Redis cart cache
    transaction.on_commit(
        lambda: invalidate_customer_cart_cache(user.id)
    )

    return {
        "message": "Guest cart merged successfully.",
        "merged_items": merged_items,
        "skipped_items": skipped_items
    }



def preserve_cart_in_session(request, user):

    # 1. Get the customer's existing database cart
    cart = Cart.objects.filter(
        customer=user
    ).first()

    # 2. If the customer has no cart, nothing to preserve
    if cart is None:
        return {}

    # 3. Get all items from the customer's cart
    cart_items = CartItem.objects.filter(
        cart=cart
    )

    # 4. Create a dictionary for the guest cart
    guest_cart = {}

    # 5. Copy product variant IDs and quantities
    for item in cart_items:

        guest_cart[str(item.product_line_id)] = item.quantity

    # 6. Store the cart in Django session
    request.session[GUEST_CART_SESSION_KEY] = guest_cart

    # 7. Tell Django that the session has changed
    request.session.modified = True

    return guest_cart



def add_to_database_cart(user, product_line_id, quantity=1):

    # 1. Validate quantity
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
        raise ValidationError({
            "quantity": "Quantity must be a positive integer."
        })

    # 2. Start database transaction
    with transaction.atomic():

        # 3. Find and lock the selected product variant
        product_line = ProductLine.objects.select_for_update().filter(
            id=product_line_id,
            is_active=True,
            seller_product__is_active=True,
            seller_product__product__is_active=True,
            seller_product__product__category__is_active=True,
            seller_product__product__product_type__is_active=True,
            seller_product__seller__is_active=True,
            seller_product__seller__verification_status="verified"
        ).first()

        if product_line is None:
            raise ValidationError(
                "This product variant is not available."
            )

        # 4. Check available stock
        if product_line.stock_qty <= 0:
            raise ValidationError("This product is out of stock.")

        # 5. Get or create customer's cart
        cart, created = Cart.objects.get_or_create(
            customer=user
        )

        # Lock the cart to avoid simultaneous updates
        cart = Cart.objects.select_for_update().get(
            id=cart.id
        )

        # 6. Get or create the cart item
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product_line=product_line,
            defaults={"quantity": 0}
        )

        # 7. Calculate new quantity
        new_quantity = cart_item.quantity + quantity

        # 8. Check stock limit
        if new_quantity > product_line.stock_qty:
            raise ValidationError({
                "quantity": (
                    f"Only {product_line.stock_qty} units are available."
                )
            })

        # 9. Update cart item quantity
        cart_item.quantity = new_quantity
        cart_item.save(
            update_fields=["quantity", "updated_at"]
        )

        # 10. Invalidate Redis cart cache after transaction commits
        transaction.on_commit(
            lambda: invalidate_customer_cart_cache(user.id)
        )

    return cart_item


def update_cart_item(user, product_line_id, quantity):

    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
        raise ValidationError({
            "quantity": "Quantity must be a positive integer."
        })

    with transaction.atomic():

        # Find the customer's cart item
        cart_item = CartItem.objects.select_for_update().filter(
            cart__customer=user,
            product_line_id=product_line_id
        ).first()

        if cart_item is None:
            raise ValidationError("Cart item not found.")

        # Lock and validate the product variant
        product_line = ProductLine.objects.select_for_update().filter(
            id=product_line_id,
            is_active=True,
            seller_product__is_active=True,
            seller_product__product__is_active=True,
            seller_product__product__category__is_active=True,
            seller_product__product__product_type__is_active=True,
            seller_product__seller__is_active=True,
            seller_product__seller__verification_status="verified"
        ).first()

        if product_line is None:
            raise ValidationError(
                "This product variant is no longer available."
            )

        if quantity > product_line.stock_qty:
            raise ValidationError({
                "quantity": f"Only {product_line.stock_qty} units are available."
            })

        # Update quantity
        cart_item.quantity = quantity
        cart_item.save(
            update_fields=["quantity", "updated_at"]
        )

        # Invalidate Redis after successful commit
        transaction.on_commit(
            lambda: invalidate_customer_cart_cache(user.id)
        )

    return cart_item


def remove_cart_item(user, product_line_id):

    # Find the customer's cart item
    cart_item = CartItem.objects.filter(
        cart__customer=user,
        product_line_id=product_line_id
    ).first()

    # Check whether item exists
    if cart_item is None:
        raise ValidationError("Cart item not found.")

    # Delete the item
    cart_item.delete()

    # Invalidate Redis cart cache
    transaction.on_commit(
        lambda: invalidate_customer_cart_cache(user.id)
    )

    return True



def clear_database_cart(user):

    # Find the customer's cart
    cart = Cart.objects.filter(
        customer=user
    ).first()

    # If cart doesn't exist, nothing to clear
    if cart is None:
        return False

    # Delete all items from the cart
    CartItem.objects.filter(
        cart=cart
    ).delete()

    # Invalidate Redis cart cache after deletion
    transaction.on_commit(
        lambda: invalidate_customer_cart_cache(user.id)
    )

    return True
