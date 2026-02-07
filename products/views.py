from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from decimal import Decimal, InvalidOperation

from products.models import Product, Category, Review, ProductListing
from cart.models import CartItem, Wishlist
from orders.models import OrderItem

def product_list(request):
    """List all products with filters and search"""
    products = Product.objects.filter(is_active=True).select_related(
        'category', 'seller', 'listing'
    ).prefetch_related('images')
    
    # Search functionality
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Category filter - handles multiple categories
    category_ids = request.GET.getlist('category')
    selected_category_ids = []
    if category_ids:
        try:
            selected_category_ids = [int(cid) for cid in category_ids if cid.isdigit()]
            if selected_category_ids:
                products = products.filter(category_id__in=selected_category_ids)
        except (ValueError, TypeError):
            pass
    
    # Organic filter
    organic = request.GET.get('organic', '')
    if organic == 'true':
        products = products.filter(is_organic=True)
    
    # Price range filter
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    
    if min_price:
        try:
            min_price_decimal = Decimal(min_price)
            products = products.filter(price__gte=min_price_decimal)
        except (ValueError, TypeError, InvalidOperation):
            min_price = ''
    
    if max_price:
        try:
            max_price_decimal = Decimal(max_price)
            products = products.filter(price__lte=max_price_decimal)
        except (ValueError, TypeError, InvalidOperation):
            max_price = ''
    
    # Stock filter
    in_stock = request.GET.get('in_stock', '')
    if in_stock == 'true':
        products = products.filter(stock_quantity__gt=0)
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    valid_sorts = [
        'price', '-price', 
        'name', '-name', 
        'rating', '-rating', 
        'created_at', '-created_at',
        'stock_quantity', '-stock_quantity'
    ]
    if sort in valid_sorts:
        products = products.order_by(sort)
    else:
        products = products.order_by('-created_at')
    
    # Get all categories for filter sidebar
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    
    # Get user's wishlist product IDs
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_categories': selected_category_ids,
        'organic': organic,
        'min_price': min_price,
        'max_price': max_price,
        'in_stock': in_stock,
        'sort': sort,
        'total_products': products.count(),
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, pk):
    """Product detail page with reviews and related products"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'seller', 'listing').prefetch_related('images'),
        pk=pk,
        is_active=True
    )
    
    # Increment view count
    if hasattr(product, 'listing'):
        product.listing.view_count += 1
        product.listing.save()
    
    # Get related products from same category
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(pk=pk).select_related('category', 'seller').prefetch_related('images')[:4]
    
    # Get product reviews with user info
    reviews = product.reviews.select_related('user').order_by('-created_at')
    
    # Calculate average rating
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Check if user has already reviewed (if authenticated)
    user_has_reviewed = False
    user_review = None
    if request.user.is_authenticated:
        user_has_reviewed = reviews.filter(user=request.user).exists()
        if user_has_reviewed:
            user_review = reviews.filter(user=request.user).first()
    
    # Check if product is in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    # Check if product is in cart
    in_cart = False
    cart_quantity = 0
    if request.user.is_authenticated:
        cart_item = CartItem.objects.filter(user=request.user, product=product).first()
        if cart_item:
            in_cart = True
            cart_quantity = cart_item.quantity
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': reviews.count(),
        'user_has_reviewed': user_has_reviewed,
        'user_review': user_review,
        'in_wishlist': in_wishlist,
        'in_cart': in_cart,
        'cart_quantity': cart_quantity,
    }
    return render(request, 'products/product_detail.html', context)


def category_products(request, category_id):
    """View products by category"""
    category = get_object_or_404(Category, pk=category_id, is_active=True)
    
    products = Product.objects.filter(
        category=category,
        is_active=True
    ).select_related('seller', 'listing').prefetch_related('images')
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    valid_sorts = ['price', '-price', 'name', '-name', 'rating', '-rating', 'created_at', '-created_at']
    if sort in valid_sorts:
        products = products.order_by(sort)
    
    context = {
        'category': category,
        'products': products,
        'sort': sort,
    }
    return render(request, 'products/category_products.html', context)


@login_required
def add_review(request, pk):
    """Add a review for a product"""
    if request.method != 'POST':
        return redirect('product_detail', pk=pk)
    
    product = get_object_or_404(Product, pk=pk)
    
    # Check if user has already reviewed
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.error(request, 'You have already reviewed this product')
        return redirect('product_detail', pk=pk)
    
    # Get form data
    rating = int(request.POST.get('rating', 5))
    comment = request.POST.get('comment', '').strip()
    
    # Validate rating
    if rating < 1 or rating > 5:
        messages.error(request, 'Invalid rating')
        return redirect('product_detail', pk=pk)
    
    # Check if user has purchased this product
    has_purchased = OrderItem.objects.filter(
        order__customer=request.user,
        product=product,
        order__status='delivered'
    ).exists()
    
    # Create review
    Review.objects.create(
        product=product,
        user=request.user,
        rating=rating,
        comment=comment,
        is_verified_purchase=has_purchased
    )
    
    # Update product average rating
    avg_rating = Review.objects.filter(product=product).aggregate(Avg('rating'))['rating__avg']
    product.rating = avg_rating or 0
    product.save()
    
    messages.success(request, '✅ Review added successfully')
    return redirect('product_detail', pk=pk)


@login_required
def delete_review(request, pk):
    """Delete a review"""
    if request.method != 'POST':
        return redirect('home')
    
    review = get_object_or_404(Review, pk=pk, user=request.user)
    product = review.product
    review.delete()
    
    # Update product average rating
    avg_rating = Review.objects.filter(product=product).aggregate(Avg('rating'))['rating__avg']
    product.rating = avg_rating or 0
    product.save()
    
    messages.success(request, 'Review deleted successfully')
    return redirect('product_detail', pk=product.pk)
