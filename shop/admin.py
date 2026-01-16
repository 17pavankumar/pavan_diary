from django.contrib import admin
from .models import (
    User, CustomerProfile, SellerProfile, Category, Product,
    ProductImage, Order, OrderItem, CartItem, Payment,
    Review, ProductListing, Wishlist
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'phone', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'loyalty_points', 'date_of_birth', 'created_at']
    search_fields = ['user__username', 'user__email']
    list_filter = ['created_at']


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'rating', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['business_name', 'business_license', 'user__username']
    ordering = ['-created_at']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductListingInline(admin.StackedInline):
    model = ProductListing
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'seller', 'price', 'stock_quantity', 'is_organic', 'rating', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_organic', 'category', 'created_at']
    search_fields = ['name', 'description', 'seller__business_name']
    ordering = ['-created_at']
    list_editable = ['price', 'stock_quantity', 'is_active']
    inlines = [ProductImageInline, ProductListingInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'status', 'total_amount', 'payment_status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'customer__username', 'customer__email', 'phone']
    ordering = ['-created_at']
    list_editable = ['status', 'payment_status']
    inlines = [OrderItemInline]
    readonly_fields = ['order_number', 'created_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'subtotal', 'created_at']
    list_filter = ['created_at']
    search_fields = ['order__order_number', 'product__name']
    readonly_fields = ['subtotal']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'get_subtotal', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']
    
    def get_subtotal(self, obj):
        return f"₹{obj.subtotal}"
    get_subtotal.short_description = 'Subtotal'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'order', 'amount', 'payment_method', 'status', 'payment_date', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_date', 'created_at']
    search_fields = ['transaction_id', 'order__order_number']
    ordering = ['-created_at']
    readonly_fields = ['transaction_id', 'created_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    ordering = ['-created_at']
    list_editable = ['is_verified_purchase']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']
    ordering = ['-created_at']


@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = ['product', 'featured', 'on_sale', 'sale_price', 'view_count', 'created_at']
    list_filter = ['featured', 'on_sale', 'created_at']
    search_fields = ['product__name']
    list_editable = ['featured', 'on_sale', 'sale_price']
    ordering = ['-view_count']


# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from .models import (
#     User, CustomerProfile, SellerProfile, Category, Product, 
#     ProductImage, Order, OrderItem, CartItem, Payment, 
#     Review, ProductListing, Wishlist
# )


# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     """Custom User Admin"""
#     list_display = ['username', 'email', 'phone', 'is_staff', 'date_joined']
#     list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']
#     search_fields = ['username', 'email', 'phone']
#     fieldsets = BaseUserAdmin.fieldsets + (
#         ('Additional Info', {'fields': ('phone', 'address')}),
#     )


# @admin.register(CustomerProfile)
# class CustomerProfileAdmin(admin.ModelAdmin):
#     """Customer Profile Admin"""
#     list_display = ['user', 'loyalty_points', 'created_at']
#     search_fields = ['user__username', 'user__email']
#     list_filter = ['created_at']


# @admin.register(SellerProfile)
# class SellerProfileAdmin(admin.ModelAdmin):
#     """Seller Profile Admin"""
#     list_display = ['business_name', 'user', 'rating', 'is_verified', 'created_at']
#     list_filter = ['is_verified', 'created_at']
#     search_fields = ['business_name', 'business_license', 'user__username']
#     list_editable = ['is_verified']


# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     """Category Admin"""
#     list_display = ['name', 'is_active', 'created_at']
#     list_filter = ['is_active', 'created_at']
#     search_fields = ['name']
#     list_editable = ['is_active']


# class ProductImageInline(admin.TabularInline):
#     """Inline for Product Images"""
#     model = ProductImage
#     extra = 1


# class ProductListingInline(admin.StackedInline):
#     """Inline for Product Listing"""
#     model = ProductListing
#     extra = 0


# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     """Product Admin with Inline Images and Listing"""
#     list_display = ['name', 'category', 'seller', 'price', 'stock_quantity', 
#                    'rating', 'is_organic', 'is_active', 'created_at']
#     list_filter = ['is_active', 'is_organic', 'category', 'created_at']
#     search_fields = ['name', 'description', 'seller__business_name']
#     list_editable = ['is_active', 'price', 'stock_quantity']
#     inlines = [ProductImageInline, ProductListingInline]
#     readonly_fields = ['rating', 'created_at', 'updated_at']
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('seller', 'category', 'name', 'description')
#         }),
#         ('Pricing & Stock', {
#             'fields': ('price', 'stock_quantity', 'unit')
#         }),
#         ('Product Details', {
#             'fields': ('is_organic', 'expiry_days', 'rating', 'is_active')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(ProductImage)
# class ProductImageAdmin(admin.ModelAdmin):
#     """Product Image Admin"""
#     list_display = ['product', 'is_primary', 'created_at']
#     list_filter = ['is_primary', 'created_at']
#     search_fields = ['product__name']


# class OrderItemInline(admin.TabularInline):
#     """Inline for Order Items"""
#     model = OrderItem
#     extra = 0
#     readonly_fields = ['subtotal']


# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     """Order Admin with Inline Items"""
#     list_display = ['order_number', 'customer', 'status', 'payment_status', 
#                    'total_amount', 'created_at']
#     list_filter = ['status', 'payment_status', 'created_at']
#     search_fields = ['order_number', 'customer__username', 'customer__email']
#     list_editable = ['status', 'payment_status']
#     inlines = [OrderItemInline]
#     readonly_fields = ['order_number', 'created_at', 'updated_at']
    
#     fieldsets = (
#         ('Order Information', {
#             'fields': ('order_number', 'customer', 'status', 'total_amount')
#         }),
#         ('Shipping Details', {
#             'fields': ('shipping_address', 'phone', 'notes')
#         }),
#         ('Payment', {
#             'fields': ('payment_method', 'payment_status')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     """Order Item Admin"""
#     list_display = ['order', 'product', 'quantity', 'price', 'subtotal']
#     search_fields = ['order__order_number', 'product__name']
#     readonly_fields = ['subtotal']


# @admin.register(CartItem)
# class CartItemAdmin(admin.ModelAdmin):
#     """Cart Item Admin"""
#     list_display = ['user', 'product', 'quantity', 'created_at']
#     list_filter = ['created_at']
#     search_fields = ['user__username', 'product__name']


# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     """Payment Admin"""
#     list_display = ['transaction_id', 'order', 'amount', 'payment_method', 
#                    'status', 'payment_date']
#     list_filter = ['status', 'payment_method', 'payment_date']
#     search_fields = ['transaction_id', 'order__order_number']
#     readonly_fields = ['transaction_id', 'created_at']


# @admin.register(Review)
# class ReviewAdmin(admin.ModelAdmin):
#     """Review Admin"""
#     list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'created_at']
#     list_filter = ['rating', 'is_verified_purchase', 'created_at']
#     search_fields = ['product__name', 'user__username', 'comment']
#     list_editable = ['is_verified_purchase']


# @admin.register(ProductListing)
# class ProductListingAdmin(admin.ModelAdmin):
#     """Product Listing Admin"""
#     list_display = ['product', 'featured', 'on_sale', 'sale_price', 'view_count']
#     list_filter = ['featured', 'on_sale', 'created_at']
#     search_fields = ['product__name']
#     list_editable = ['featured', 'on_sale', 'sale_price']


# # Customize Admin Site Header
# admin.site.site_header = "Pavan Diary Admin"
# admin.site.site_title = "Pavan Diary Admin Portal"
# admin.site.index_title = "Welcome to Pavan Diary Administration"






# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from .models import (
#     User, CustomerProfile, SellerProfile, Category, Product, 
#     ProductImage, Order, OrderItem, CartItem, Payment, 
#     Review, ProductListing
# )

# # Register your models here.


# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     """Custom User Admin"""
#     list_display = ['username', 'email', 'phone', 'is_staff', 'date_joined']
#     list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']
#     search_fields = ['username', 'email', 'phone']
#     fieldsets = BaseUserAdmin.fieldsets + (
#         ('Additional Info', {'fields': ('phone', 'address')}),
#     )


# @admin.register(CustomerProfile)
# class CustomerProfileAdmin(admin.ModelAdmin):
#     """Customer Profile Admin"""
#     list_display = ['user', 'loyalty_points', 'created_at']
#     search_fields = ['user__username', 'user__email']
#     list_filter = ['created_at']


# @admin.register(SellerProfile)
# class SellerProfileAdmin(admin.ModelAdmin):
#     """Seller Profile Admin"""
#     list_display = ['business_name', 'user', 'rating', 'is_verified', 'created_at']
#     list_filter = ['is_verified', 'created_at']
#     search_fields = ['business_name', 'business_license', 'user__username']
#     list_editable = ['is_verified']


# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     """Category Admin"""
#     list_display = ['name', 'is_active', 'created_at']
#     list_filter = ['is_active', 'created_at']
#     search_fields = ['name']
#     list_editable = ['is_active']


# class ProductImageInline(admin.TabularInline):
#     """Inline for Product Images"""
#     model = ProductImage
#     extra = 1


# class ProductListingInline(admin.StackedInline):
#     """Inline for Product Listing"""
#     model = ProductListing
#     extra = 0


# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     """Product Admin with Inline Images and Listing"""
#     list_display = ['name', 'category', 'seller', 'price', 'stock_quantity', 
#                    'rating', 'is_organic', 'is_active', 'created_at']
#     list_filter = ['is_active', 'is_organic', 'category', 'created_at']
#     search_fields = ['name', 'description', 'seller__business_name']
#     list_editable = ['is_active', 'price', 'stock_quantity']
#     inlines = [ProductImageInline, ProductListingInline]
#     readonly_fields = ['rating', 'created_at', 'updated_at']
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('seller', 'category', 'name', 'description')
#         }),
#         ('Pricing & Stock', {
#             'fields': ('price', 'stock_quantity', 'unit')
#         }),
#         ('Product Details', {
#             'fields': ('is_organic', 'expiry_days', 'rating', 'is_active')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(ProductImage)
# class ProductImageAdmin(admin.ModelAdmin):
#     """Product Image Admin"""
#     list_display = ['product', 'is_primary', 'created_at']
#     list_filter = ['is_primary', 'created_at']
#     search_fields = ['product__name']


# class OrderItemInline(admin.TabularInline):
#     """Inline for Order Items"""
#     model = OrderItem
#     extra = 0
#     readonly_fields = ['subtotal']


# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     """Order Admin with Inline Items"""
#     list_display = ['order_number', 'customer', 'status', 'payment_status', 
#                    'total_amount', 'created_at']
#     list_filter = ['status', 'payment_status', 'created_at']
#     search_fields = ['order_number', 'customer__username', 'customer__email']
#     list_editable = ['status', 'payment_status']
#     inlines = [OrderItemInline]
#     readonly_fields = ['order_number', 'created_at', 'updated_at']
    
#     fieldsets = (
#         ('Order Information', {
#             'fields': ('order_number', 'customer', 'status', 'total_amount')
#         }),
#         ('Shipping Details', {
#             'fields': ('shipping_address', 'phone', 'notes')
#         }),
#         ('Payment', {
#             'fields': ('payment_method', 'payment_status')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     """Order Item Admin"""
#     list_display = ['order', 'product', 'quantity', 'price', 'subtotal']
#     search_fields = ['order__order_number', 'product__name']
#     readonly_fields = ['subtotal']


# @admin.register(CartItem)
# class CartItemAdmin(admin.ModelAdmin):
#     """Cart Item Admin"""
#     list_display = ['user', 'product', 'quantity', 'created_at']
#     list_filter = ['created_at']
#     search_fields = ['user__username', 'product__name']


# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     """Payment Admin"""
#     list_display = ['transaction_id', 'order', 'amount', 'payment_method', 
#                    'status', 'payment_date']
#     list_filter = ['status', 'payment_method', 'payment_date']
#     search_fields = ['transaction_id', 'order__order_number']
#     readonly_fields = ['transaction_id', 'created_at']


# @admin.register(Review)
# class ReviewAdmin(admin.ModelAdmin):
#     """Review Admin"""
#     list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'created_at']
#     list_filter = ['rating', 'is_verified_purchase', 'created_at']
#     search_fields = ['product__name', 'user__username', 'comment']
#     list_editable = ['is_verified_purchase']


# @admin.register(ProductListing)
# class ProductListingAdmin(admin.ModelAdmin):
#     """Product Listing Admin"""
#     list_display = ['product', 'featured', 'on_sale', 'sale_price', 'view_count']
#     list_filter = ['featured', 'on_sale', 'created_at']
#     search_fields = ['product__name']
#     list_editable = ['featured', 'on_sale', 'sale_price']


# # Customize Admin Site Header
# admin.site.site_header = "FreshDairy Admin"
# admin.site.site_title = "FreshDairy Admin Portal"
# admin.site.index_title = "Welcome to FreshDairy Administration"