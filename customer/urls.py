
from django.urls import path

from .views import (
    CustomerProductListView,
    CustomerProductDetailView,
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
]
