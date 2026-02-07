from django.shortcuts import render
from products.models import Product, Category

def home(request):
    """Homepage with featured products and categories"""
    featured_products = Product.objects.filter(
        is_active=True,
        listing__featured=True
    ).select_related('category', 'seller', 'listing').prefetch_related('images')[:8]
    
    categories = Category.objects.filter(is_active=True)
    
    # Get new arrivals
    new_arrivals = Product.objects.filter(
        is_active=True
    ).select_related('category', 'seller').prefetch_related('images').order_by('-created_at')[:4]
    
    # Get organic products
    organic_products = Product.objects.filter(
        is_active=True,
        is_organic=True
    ).select_related('category', 'seller').prefetch_related('images')[:4]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'new_arrivals': new_arrivals,
        'organic_products': organic_products,
    }
    return render(request, 'core/home.html', context)
