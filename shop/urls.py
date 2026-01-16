"""
Pavan Diary E-commerce - URLs Configuration
Complete URL patterns for all features - FINAL VERSION
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from shop import views

urlpatterns = [
    # ==================== ADMIN ====================
    path('admin/', admin.site.urls),
    
    # ==================== HOME ====================
    path('', views.home, name='home'),
    
    # ==================== PRODUCTS ====================
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),
    
    # ==================== CART ====================
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    
    # ==================== WISHLIST ====================
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:pk>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:pk>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/toggle/<int:pk>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/move-all/', views.move_all_to_cart, name='move_all_to_cart'),
    path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),
    
    # ==================== CHECKOUT & PAYMENT ====================
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<int:order_id>/', views.payment, name='payment'),
    
    # ==================== ORDERS ====================
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    
    # ==================== REVIEWS ====================
    path('products/<int:pk>/review/', views.add_review, name='add_review'),
    path('reviews/<int:pk>/delete/', views.delete_review, name='delete_review'),
    
    # ==================== AUTHENTICATION ====================
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('password-reset/', views.password_reset, name='password_reset'),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)



# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# from shop import views

# urlpatterns = [
#     # Admin
#     path('admin/', admin.site.urls),
    
#     # Home
#     path('', views.home, name='home'),
    
#     # Products
#     path('products/', views.product_list, name='product_list'),
#     path('products/<int:pk>/', views.product_detail, name='product_detail'),
    
#     # Cart
#     path('cart/', views.cart, name='cart'),
#     path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
#     path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
#     path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    
#     # Wishlist
#     path('wishlist/', views.wishlist, name='wishlist'),
#     path('wishlist/add/<int:pk>/', views.add_to_wishlist, name='add_to_wishlist'),
#     path('wishlist/remove/<int:pk>/', views.remove_from_wishlist, name='remove_from_wishlist'),
#     path('wishlist/move-all/', views.move_all_to_cart, name='move_all_to_cart'),
#     path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),
    
#     # Checkout & Payment
#     path('checkout/', views.checkout, name='checkout'),
#     path('payment/<int:order_id>/', views.payment, name='payment'),
    
#     # Orders
#     path('orders/', views.order_list, name='order_list'),
#     path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
#     # Authentication
#     path('register/', views.register, name='register'),
#     path('login/', views.user_login, name='login'),
#     path('logout/', views.user_logout, name='logout'),
#     path('profile/', views.profile, name='profile'),
#     path('password-reset/', views.password_reset, name='password_reset'),
# ]

# # Serve media files in development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# from shop import views

# urlpatterns = [
#     path('admin/', admin.site.urls),
    
#     # Home
#     path('', views.home, name='home'),
    
#     # Products
#     path('products/', views.product_list, name='product_list'),
#     path('products/<int:pk>/', views.product_detail, name='product_detail'),
    
#     # Cart
#     path('cart/', views.cart, name='cart'),
#     path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
#     path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
#     path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    
#     # Wishlist
#     path('wishlist/', views.wishlist, name='wishlist'),
#     path('wishlist/add/<int:pk>/', views.add_to_wishlist, name='add_to_wishlist'),
#     path('wishlist/remove/<int:pk>/', views.remove_from_wishlist, name='remove_from_wishlist'),
#     path('wishlist/move-all/', views.move_all_to_cart, name='move_all_to_cart'),
#     path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),
    
#     # Checkout & Payment
#     path('checkout/', views.checkout, name='checkout'),
#     path('payment/<int:order_id>/', views.payment, name='payment'),
    
#     # Orders
#     path('orders/', views.order_list, name='order_list'),
#     path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
#     # Auth
#     path('register/', views.register, name='register'),
#     path('login/', views.user_login, name='login'),
#     path('logout/', views.user_logout, name='logout'),
#     path('profile/', views.profile, name='profile'),
#     path('password-reset/', views.password_reset, name='password_reset'),
# ]

# # Serve media files in development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# from shop import views

# urlpatterns = [
#     path('admin/', admin.site.urls),
    
#     # Home
#     path('', views.home, name='home'),
    
#     # Products
#     path('products/', views.product_list, name='product_list'),
#     path('products/<int:pk>/', views.product_detail, name='product_detail'),
    
#     # Cart
#     path('cart/', views.cart, name='cart'),
#     path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
#     path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
#     path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    
#     # Checkout & Payment
#     path('checkout/', views.checkout, name='checkout'),
#     path('payment/<int:order_id>/', views.payment, name='payment'),
    
#     # Orders
#     path('orders/', views.order_list, name='order_list'),
#     path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
#     # Auth
#     path('register/', views.register, name='register'),
#     path('login/', views.user_login, name='login'),
#     path('logout/', views.user_logout, name='logout'),
#     path('profile/', views.profile, name='profile'),
#     path('password-reset/', views.password_reset, name='password_reset'),
# ]

# # Serve media files in development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)