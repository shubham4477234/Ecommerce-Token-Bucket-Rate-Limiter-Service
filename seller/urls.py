from django.urls import path
from .views import ProductImageListView, ProductImageUploadView,ProductVariantCreateView,AddProductToStoreView,ProductRequestView, ProductVariantUpdateView, SellerDashboardView, SellerProductUpdateView,SellerProfileView, CategoryListView, ProductTypeListView, ProductTypeAttributeView, ProductCatalogueView


urlpatterns = [
    path("profile/",SellerProfileView.as_view(),name="seller-profile"),
    path("categories/",CategoryListView.as_view(),name="seller-categories"),
    path("product-types/",ProductTypeListView.as_view(),name="seller-product-types"),
    path("product-types/<int:product_type_id>/attributes/",ProductTypeAttributeView.as_view(),name="product-type-attributes"),
    path("catalog/products/",ProductCatalogueView.as_view(),name="product-catalogue"),
    path("catalog/products/request/", ProductRequestView.as_view(), name="product-request"),
    path( "products/", AddProductToStoreView.as_view(),  name="seller-products"),
    path( "products/<int:pk>/", SellerProductUpdateView.as_view(), name="seller-product-update"),
    path( "products/<int:pk>/variants/", ProductVariantCreateView.as_view(), name="product-variant-create"),
    path( "variants/<int:pk>/", ProductVariantUpdateView.as_view(), name="seller-variant-update"),
    path( "products/<int:pk>/images/", ProductImageUploadView.as_view() ,name="seller-product-image-upload"),
    path( "products/<int:pk>/images/", ProductImageListView.as_view(), name="seller-product-image-list"),
    path( "dashboard/", SellerDashboardView.as_view(),  name="seller-dashboard"),
    ]