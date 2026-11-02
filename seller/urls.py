from django.urls import path
from .views import AddProductToStoreView,ProductRequestView,SellerProfileView, CategoryListView, ProductTypeListView, ProductTypeAttributeView, ProductCatalogueView


urlpatterns = [
    path("profile/",SellerProfileView.as_view(),name="seller-profile"),
    path("categories/",CategoryListView.as_view(),name="seller-categories"),
    path("product-types/",ProductTypeListView.as_view(),name="seller-product-types"),
    path("product-types/<int:product_type_id>/attributes/",ProductTypeAttributeView.as_view(),name="product-type-attributes"),
    path("catalog/products/",ProductCatalogueView.as_view(),name="product-catalogue"),
    path("catalog/products/request/", ProductRequestView.as_view(), name="product-request"),
    path( "products/", AddProductToStoreView.as_view(),  name="seller-products"),
]