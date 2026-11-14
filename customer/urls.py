
from django.urls import path

from .views import (
    CustomerProductListView,
    CustomerProductDetailView,
    CustomerCategoryListView,
    CustomerCartView,
)


urlpatterns = [
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

    path(
    "categories/",
    CustomerCategoryListView.as_view(),
    name="customer-categories"
    ),

    path(
    "cart/",
    CustomerCartView.as_view(),
    name="customer-cart"
   ),
]
