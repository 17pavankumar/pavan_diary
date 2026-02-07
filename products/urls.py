from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),
    path('products/<int:pk>/review/', views.add_review, name='add_review'),
    path('reviews/<int:pk>/delete/', views.delete_review, name='delete_review'),
]
