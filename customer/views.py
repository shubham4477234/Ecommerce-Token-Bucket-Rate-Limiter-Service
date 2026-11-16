
from django.db.models import Prefetch
import hashlib
import json
from django.core.cache import cache
from httpx2 import patch
from polars import Decimal
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from seller.models import SellerProduct, ProductLine, Category
from rest_framework import status, serializers
from .serializers import CustomerProductListSerializer, CustomerProductDetailSerializer, CustomerCategorySerializer,AddToCartSerializer, CartItemSerializer,UpdateCartItemSerializer, AddressSerializer, PlaceOrderSerializer
from .pagination import CustomerProductPagination
from config.cache_utils import (
    CUSTOMER_PRODUCT_LIST_VERSION_KEY,
)
from customer.models import Cart, CartItem
from .models import Cart, CartItem, Order, OrderItem
from customer.serializers import CartSerializer
from .services import add_to_guest_cart, add_to_database_cart, update_cart_item, remove_cart_item, clear_database_cart
from rest_framework.exceptions import ValidationError
from customer.models import Address
from django.db import transaction

class CustomerProductListView(ListAPIView):

    serializer_class = CustomerProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomerProductPagination

    def get_queryset(self):

        # Get active variants that have stock available
        available_variants = (
            ProductLine.objects
            .filter(
                is_active=True,
                stock_qty__gt=0
            )
            .prefetch_related(
                "attribute_values__attribute_value__attribute"
            )
            .order_by("id")
        )

        # Get active and verified seller product listings
        return (
            SellerProduct.objects
            .filter(
                is_active=True,
                product__is_active=True,
                product__category__is_active=True,
                product__product_type__is_active=True,
                seller__is_active=True,
                seller__verification_status="verified",
                product_lines__is_active=True,
                product_lines__stock_qty__gt=0,
            )
            .select_related(
                "product",
                "product__category",
                "product__product_type",
                "seller",
            )
            .prefetch_related(
                "images",
                Prefetch(
                    "product_lines",
                    queryset=available_variants,
                    to_attr="available_product_lines",
                ),
            )
            .distinct()
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):

        # Get current listing cache version
        version = cache.get(
            CUSTOMER_PRODUCT_LIST_VERSION_KEY,
            1
        )

        # Include query parameters in cache key
        query_string = request.GET.urlencode()

        query_hash = hashlib.md5(
            query_string.encode()
        ).hexdigest()

        # Include domain and protocol in cache key
        request_host = request.build_absolute_uri("/")

        cache_key = (
            f"customer:products:list:"
            f"{request_host}:v{version}:{query_hash}"
        )

        # Check Redis cache
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        # Cache miss: fetch data from PostgreSQL
        response = super().list(
            request,
            *args,
            **kwargs
        )

        # Convert response into JSON-compatible data
        response_data = response.data

        cache_data = json.loads(
            JSONRenderer().render(response_data)
        )

        # Store response in Redis for 120 seconds
        cache.set(
            cache_key,
            cache_data,
            timeout=120
        )

        return Response(response_data)



class CustomerProductDetailView(RetrieveAPIView):

    serializer_class = CustomerProductDetailSerializer
    permission_classes = [AllowAny]

    lookup_field = "id"

    def get_queryset(self):

        # Get all active variants, including out-of-stock variants
        available_variants = (
            ProductLine.objects
            .filter(
                is_active=True
            )
            .prefetch_related(
                "attribute_values__attribute_value__attribute"
            )
            .order_by("id")
        )

        # Get active and verified seller product listings
        return (
            SellerProduct.objects
            .filter(
                is_active=True,
                product__is_active=True,
                product__category__is_active=True,
                product__product_type__is_active=True,
                seller__is_active=True,
                seller__verification_status="verified",
            )
            .select_related(
                "product",
                "product__category",
                "product__product_type",
                "seller",
            )
            .prefetch_related(
                "images",
                Prefetch(
                    "product_lines",
                    queryset=available_variants,
                    to_attr="detail_product_lines",
                ),
            )
        )

    
def retrieve(self, request, *args, **kwargs):

    # Get seller product listing ID
    seller_product_id = kwargs["pk"]

    # Include domain and protocol in cache key
    request_host = request.build_absolute_uri("/")

    # Get the current cache version for this listing
    detail_version_key = (
        f"customer:products:detail:version:{seller_product_id}"
    )

    version = cache.get(detail_version_key, 1)

    # Create a host-aware and versioned cache key
    cache_key = (
        f"customer:products:detail:"
        f"{request_host}:{seller_product_id}:v{version}"
    )

    # Check Redis cache
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return Response(cached_data)

    # Cache miss: fetch product details from PostgreSQL
    response = super().retrieve(
        request,
        *args,
        **kwargs
    )

    # Convert response into JSON-compatible data
    cache_data = json.loads(
        JSONRenderer().render(response.data)
    )

    # Store response in Redis for 5 minutes
    cache.set(
        cache_key,
        cache_data,
        timeout=300
    )

    return Response(response.data)


class CustomerCategoryListView(ListAPIView):

    serializer_class = CustomerCategorySerializer
    permission_classes = [AllowAny]

    CACHE_KEY = "customer:categories:tree"
    CACHE_TIMEOUT = 600  # 10 minutes

    def list(self, request, *args, **kwargs):

        # Check Redis first
        cached_data = cache.get(self.CACHE_KEY)

        if cached_data is not None:
            return Response(cached_data)

        # Fetch active categories
        categories = Category.objects.filter(
            is_active=True
        ).order_by("tree_id", "lft")

        # Load the complete category tree efficiently
        categories = categories.get_cached_trees()

        # Serialize categories
        serializer = self.get_serializer(
            categories,
            many=True
        )

        # Save response in Redis
        cache.set(
            self.CACHE_KEY,
            serializer.data,
            timeout=self.CACHE_TIMEOUT
        )

        return Response(serializer.data)



class CustomerCartView(RetrieveAPIView):

    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):

        # 1. Check whether customer is authenticated
        if request.user.is_authenticated:

            customer_id = request.user.id
            cache_key = f"customer:cart:{customer_id}"

            # 2. Check Redis cache
            cached_data = cache.get(cache_key)

            if cached_data is not None:
                return Response(cached_data)

            # 3. Get or create customer's database cart
            cart, created = Cart.objects.get_or_create(
                customer=request.user
            )

            # 4. Fetch cart items efficiently
            cart = Cart.objects.prefetch_related(
                "items__product_line__seller_product__product",
                "items__product_line__seller_product__seller"
            ).get(id=cart.id)

            # 5. Serialize database cart
            serializer = self.get_serializer(cart)

            response_data = {
                "cart_type": "database",
                **serializer.data
            }

            # 6. Cache response in Redis for 5 minutes
            cache.set(
                cache_key,
                response_data,
                timeout=300
            )

            return Response(response_data)

        # ---------------------------------
        # GUEST CUSTOMER CART
        # ---------------------------------

        # 7. Get guest cart from Django session
        guest_cart = request.session.get(
            "guest_cart",
            {}
        )

        if not guest_cart:
            return Response({
                "cart_type": "session",
                "items": [],
                "total_items": 0,
                "total_amount": "0.00"
            })

        # 8. Validate session cart data
        valid_items = {}

        for product_line_id, quantity in guest_cart.items():

            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, int)
                or quantity <= 0
            ):
                continue

            try:
                product_line_id = int(product_line_id)
            except (ValueError, TypeError):
                continue

            if product_line_id > 0:
                valid_items[product_line_id] = quantity

        # 9. Fetch product variants from database
        product_lines = ProductLine.objects.filter(
            id__in=valid_items.keys()
        ).select_related(
            "seller_product__product",
            "seller_product__seller"
        )

        product_line_map = {
            product_line.id: product_line
            for product_line in product_lines
        }

        # 10. Create temporary CartItem objects
        # These objects are NOT saved in PostgreSQL
        guest_items = []

        for product_line_id, quantity in valid_items.items():

            product_line = product_line_map.get(product_line_id)

            if product_line is None:
                continue

            guest_items.append(
                CartItem(
                    product_line=product_line,
                    quantity=quantity
                )
            )

        # 11. Serialize guest cart items
        items_serializer = CartItemSerializer(
            guest_items,
            many=True
        )

        # 12. Calculate cart totals
        total_items = sum(
            item.quantity for item in guest_items
        )

        total_amount = sum(
            (
                item.product_line.price * item.quantity
                for item in guest_items
            ),
            start=Decimal("0.00")
        )

        # 13. Return guest cart response
        return Response({
            "cart_type": "session",
            "items": items_serializer.data,
            "total_items": total_items,
            "total_amount": total_amount
        })




class AddToCartView(APIView):

    # Allow both guest and authenticated customers
    permission_classes = [AllowAny]

    def post(self, request):

        # 1. Validate incoming request data
        serializer = AddToCartSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Get validated data
        product_line_id = serializer.validated_data["product_line_id"]
        quantity = serializer.validated_data["quantity"]

        # 3. Check whether customer is logged in
        if request.user.is_authenticated:

            # Save item in PostgreSQL database
            cart_item = add_to_database_cart(
                request.user,
                product_line_id,
                quantity
            )

            return Response(
                {
                    "message": "Product added to your cart successfully.",
                    "cart_type": "database",
                    "product_line_id": cart_item.product_line_id,
                    "quantity": cart_item.quantity
                },
                status=status.HTTP_200_OK
            )

        # 4. Guest customer: save item in Django session
        guest_cart = add_to_guest_cart(
            request,
            product_line_id,
            quantity
        )

        return Response(
            {
                "message": "Product added to guest cart successfully.",
                "cart_type": "session",
                "cart": guest_cart
            },
            status=status.HTTP_200_OK
        )



class UpdateCartItemView(APIView):

    permission_classes = [AllowAny]

    def patch(self, request, product_line_id):

        # Validate request
        serializer = UpdateCartItemSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        quantity = serializer.validated_data["quantity"]

        # Logged-in customer
        if request.user.is_authenticated:

            cart_item = update_cart_item(
                request.user,
                product_line_id,
                quantity
            )

            return Response({
                "message": "Cart quantity updated successfully.",
                "cart_type": "database",
                "product_line_id": cart_item.product_line_id,
                "quantity": cart_item.quantity
            })

        # Guest customer
        guest_cart = request.session.get("guest_cart", {})

        product_key = str(product_line_id)

        if product_key not in guest_cart:
            return Response(
                {"message": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate product availability
        product_line = ProductLine.objects.filter(
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
            return Response(
                {"message": "This product variant is unavailable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity > product_line.stock_qty:
            return Response(
                {
                    "quantity": (
                        f"Only {product_line.stock_qty} units are available."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update session cart
        guest_cart[product_key] = quantity

        request.session["guest_cart"] = guest_cart
        request.session.modified = True

        return Response({
            "message": "Cart quantity updated successfully.",
            "cart_type": "session",
            "product_line_id": product_line_id,
            "quantity": quantity
        })


class RemoveCartItemView(APIView):

    permission_classes = [AllowAny]

    def delete(self, request, product_line_id):

        # Logged-in customer
        if request.user.is_authenticated:

            remove_cart_item(
                request.user,
                product_line_id
            )

            return Response(
                {
                    "message": "Cart item removed successfully.",
                    "cart_type": "database"
                },
                status=status.HTTP_200_OK
            )

        # Guest customer
        guest_cart = request.session.get(
            "guest_cart",
            {}
        )

        product_key = str(product_line_id)

        # Check whether item exists
        if product_key not in guest_cart:
            return Response(
                {"message": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Remove item from session
        del guest_cart[product_key]

        request.session["guest_cart"] = guest_cart
        request.session.modified = True

        return Response(
            {
                "message": "Cart item removed successfully.",
                "cart_type": "session"
            },
            status=status.HTTP_200_OK
        )


class ClearCartView(APIView):

    permission_classes = [AllowAny]

    def delete(self, request):

        # Logged-in customer
        if request.user.is_authenticated:

            clear_database_cart(request.user)

            return Response(
                {
                    "message": "Cart cleared successfully.",
                    "cart_type": "database"
                },
                status=status.HTTP_200_OK
            )

        # Guest customer
        request.session["guest_cart"] = {}
        request.session.modified = True

        return Response(
            {
                "message": "Cart cleared successfully.",
                "cart_type": "session"
            },
            status=status.HTTP_200_OK
        )



class CustomerAddressView(APIView):

    permission_classes = [IsAuthenticated]

    # GET: List all addresses of the logged-in customer
    def get(self, request):

        addresses = Address.objects.filter(
            customer=request.user
        ).order_by("-is_default", "-created_at")

        serializer = AddressSerializer(
            addresses,
            many=True
        )

        return Response(
            {
                "message": "Addresses fetched successfully.",
                "total_addresses": addresses.count(),
                "addresses": serializer.data
            },
            status=status.HTTP_200_OK
        )

    # POST: Add a new address
    def post(self, request):

        serializer = AddressSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        is_default = serializer.validated_data.get(
            "is_default", False
        )

        with transaction.atomic():

            # Remove previous default address if necessary
            if is_default:
                Address.objects.filter(
                    customer=request.user,
                    is_default=True
                ).update(is_default=False)

            # Assign address to authenticated customer
            address = serializer.save(
                customer=request.user
            )

        return Response(
            {
                "message": "Address added successfully.",
                "address": AddressSerializer(address).data
            },
            status=status.HTTP_201_CREATED
        )

    # PATCH: Update an existing address
    def patch(self, request, address_id):

        # Find address belonging to logged-in customer
        address = Address.objects.filter(
            id=address_id,
            customer=request.user
        ).first()

        if address is None:
            return Response(
                {"message": "Address not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate updated data
        serializer = AddressSerializer(
            address,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check default address preference
        is_default = serializer.validated_data.get(
            "is_default",
            address.is_default
        )

        with transaction.atomic():

            # Unset previous default address
            if is_default:
                Address.objects.filter(
                    customer=request.user,
                    is_default=True
                ).exclude(
                    id=address.id
                ).update(is_default=False)

            # Save updated address
            updated_address = serializer.save()

        return Response(
            {
                "message": "Address updated successfully.",
                "address": AddressSerializer(updated_address).data
            },
            status=status.HTTP_200_OK
        )

 
    def delete(self, request, address_id):

    # Find address belonging to logged-in customer
        address = Address.objects.filter(
        id=address_id,
        customer=request.user
        ).first()

        if address is None:
            return Response(
            {"message": "Address not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Delete the address
        address.delete()

        return Response(
        {"message": "Address deleted successfully."},
        status=status.HTTP_200_OK
    )



class PlaceOrderView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        # 1. Validate the selected delivery address
        serializer = PlaceOrderSerializer(
            data=request.data,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)

        address = serializer.validated_data["address_id"]

        # 2. Start database transaction
        with transaction.atomic():

            # Lock the customer's cart
            cart = Cart.objects.select_for_update().filter(
                customer=request.user
            ).first()

            if cart is None:
                return Response(
                    {"message": "Your cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Lock cart items
            cart_items = list(
                CartItem.objects.select_for_update()
                .filter(cart=cart)
                .order_by("id")
            )

            if not cart_items:
                return Response(
                    {"message": "Your cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            locked_items = []
            total_amount = Decimal("0.00")

            # 3. Lock and validate each product's stock
            for cart_item in cart_items:

                try:
                    product_line = ProductLine.objects.select_for_update().get(
                        id=cart_item.product_line_id
                    )
                except ProductLine.DoesNotExist:
                    raise serializers.ValidationError(
                        "One of the products in your cart is unavailable."
                    )

                seller_product = product_line.seller_product
                product = seller_product.product
                seller = seller_product.seller

                # Check product and seller availability
                if (
                    not product_line.is_active
                    or not seller_product.is_active
                    or not product.is_active
                    or not seller.is_active
                    or seller.verification_status != "verified"
                    or not product.category.is_active
                    or not product.product_type.is_active
                ):
                    raise serializers.ValidationError(
                        f"{product.name} is currently unavailable."
                    )

                # Check stock
                if product_line.stock_qty < cart_item.quantity:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {product.name}. "
                        f"Available stock: {product_line.stock_qty}"
                    )

                # Calculate subtotal using database price
                subtotal = product_line.price * cart_item.quantity

                total_amount += subtotal

                locked_items.append({
                    "product_line": product_line,
                    "product_name": product.name,
                    "seller_name": seller.store_name,
                    "sku": product_line.sku,
                    "unit_price": product_line.price,
                    "quantity": cart_item.quantity,
                    "subtotal": subtotal,
                })

            # 4. Create Order with address snapshot
            order = Order.objects.create(
                customer=request.user,
                status="placed",
                payment_method="cod",
                payment_status="pending",

                full_name=address.full_name,
                phone=address.phone,
                address_line_1=address.address_line_1,
                address_line_2=address.address_line_2,
                city=address.city,
                state=address.state,
                postal_code=address.postal_code,
                country=address.country,

                total_amount=total_amount
            )

            # 5. Create OrderItems and deduct stock
            response_items = []

            for item in locked_items:

                OrderItem.objects.create(
                    order=order,
                    product_line=item["product_line"],
                    product_name=item["product_name"],
                    seller_name=item["seller_name"],
                    sku=item["sku"],
                    unit_price=item["unit_price"],
                    quantity=item["quantity"],
                    subtotal=item["subtotal"]
                )

                # Deduct purchased quantity
                product_line = item["product_line"]
                product_line.stock_qty -= item["quantity"]

                product_line.save(update_fields=["stock_qty"])

                response_items.append({
                    "product_name": item["product_name"],
                    "seller_name": item["seller_name"],
                    "sku": item["sku"],
                    "unit_price": str(item["unit_price"]),
                    "quantity": item["quantity"],
                    "subtotal": str(item["subtotal"])
                })

            # 6. Clear cart after successful order creation
            cart_items_queryset = CartItem.objects.filter(cart=cart)
            cart_items_queryset.delete()

            # Invalidate the customer's cached cart after commit
            transaction.on_commit(
                lambda: cache.delete(
                    f"customer:cart:{request.user.id}"
                )
            )

        # 7. Return order confirmation
        return Response(
            {
                "message": "Order placed successfully!",
                "order": {
                    "order_number": str(order.order_number),
                    "status": order.status,
                    "payment_method": order.payment_method,
                    "payment_status": order.payment_status,
                    "total_amount": str(order.total_amount),
                    "items": response_items,
                    "delivery_address": {
                        "full_name": order.full_name,
                        "phone": order.phone,
                        "address_line_1": order.address_line_1,
                        "address_line_2": order.address_line_2,
                        "city": order.city,
                        "state": order.state,
                        "postal_code": order.postal_code,
                        "country": order.country
                    }
                }
            },
            status=status.HTTP_201_CREATED
        )
