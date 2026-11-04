from django.urls import path
from .views import AdminCategoryCreateView, AdminCategoryUpdateView, AdminProductTypeCreateView,AdminRejectProductRequestView,AdminProductRequestListView, AdminProductRequestDetailView,AdminApproveProductRequestView,AdminAttributeConfigurationView


urlpatterns = [
    path( "product-requests/", AdminProductRequestListView.as_view(), name="admin-product-requests"),
     # API 2 - View product request details
    path( "product-requests/<int:pk>/", AdminProductRequestDetailView.as_view(), name="admin-product-request-detail"),
    # API 3 - Approve a product request
    path( "product-requests/<int:pk>/approve/", AdminApproveProductRequestView.as_view(), name="admin-approve-product-request"),
    path( "product-requests/<int:pk>/reject/", AdminRejectProductRequestView.as_view(), name="admin-reject-product-request"),
    path( "categories/", AdminCategoryCreateView.as_view(),  name="admin-category-create"),
    path( "categories/<int:pk>/", AdminCategoryUpdateView.as_view(), name="admin-category-update"),
    path( "product-types/", AdminProductTypeCreateView.as_view(), name="admin-product-type-create"),
    path( "attributes/", AdminAttributeConfigurationView.as_view(), name="admin-attribute-configuration"),
]