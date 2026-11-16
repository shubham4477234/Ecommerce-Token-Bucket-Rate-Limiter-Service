
from django.urls import path

from .views import (
    CustomerProductListView,
    CustomerProductDetailView,
    CustomerCategoryListView,
    CustomerCartView,
    AddToCartView,
    UpdateCartItemView,
    RemoveCartItemView,
    ClearCartView,
    CustomerAddressView,
    PlaceOrderView,
)


urlpatterns = [

    # --------------------------------
    # PRODUCT APIs
    # --------------------------------

    path(
        "products/",
        CustomerProductListView.as_view(),
        name="customer-product-list",
    ),

    path(
        "products/<int:pk>/",
        CustomerProductDetailView.as_view(),
        name="customer-product-detail",
    ),

    # --------------------------------
    # CATEGORY API
    # --------------------------------

    path(
        "categories/",
        CustomerCategoryListView.as_view(),
        name="customer-categories",
    ),

    # --------------------------------
    # CART APIs
    # --------------------------------

    # GET: Retrieve cart
    # DELETE: Clear cart
    path(
        "cart/",
        CustomerCartView.as_view(),
        name="customer-cart",
    ),

    # POST: Add item to cart
    path(
        "cart/items/",
        AddToCartView.as_view(),
        name="add-to-cart",
    ),

    # PATCH: Update item quantity
    # DELETE: Remove item
    path(
        "cart/items/<int:product_line_id>/",
        UpdateCartItemView.as_view(),
        name="update-cart-item",
    ),

    # --------------------------------
    # ADDRESS APIs
    # --------------------------------

    # GET: List addresses
    # POST: Add address
    path(
        "addresses/",
        CustomerAddressView.as_view(),
        name="customer-addresses",
    ),

    # PATCH: Update address
    # DELETE: Delete address
    path(
        "addresses/<int:address_id>/",
        CustomerAddressView.as_view(),
        name="customer-address-detail",
    ),

    path(
        "orders/place/",
        PlaceOrderView.as_view(),
        name="place-order"
    ),
]
