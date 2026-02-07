from django.contrib import admin
from .models import Category, Product, ProductListing, ProductImage, Review

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductListingInline(admin.StackedInline):
    model = ProductListing
    can_delete = False
    verbose_name_plural = 'Product Listing'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    search_fields = ['name']
    list_filter = ['is_active']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity', 'rating', 'is_active']
    list_filter = ['category', 'is_active', 'is_organic']
    search_fields = ['name', 'description']
    inlines = [ProductImageInline, ProductListingInline]
    readonly_fields = ['rating', 'created_at', 'updated_at']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']

# Optionally register ProductListing if needed as standalone
# admin.site.register(ProductListing)
