"""
Pavan Diary E-commerce - Views
Complete view functions for all features - FINAL VERSION
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q, Avg, Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import (
    User, CustomerProfile, SellerProfile, Category, Product, 
    ProductImage, Order, OrderItem, CartItem, Payment, 
    Review, ProductListing, Wishlist
)
from decimal import Decimal, InvalidOperation
import uuid
from datetime import datetime


# ==================== PUBLIC VIEWS ====================

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
    return render(request, 'shop/home.html', context)


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
        # Convert to integers and filter
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
    }
    return render(request, 'shop/product_list.html', context)


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
    return render(request, 'shop/product_detail.html', context)


# ==================== CART VIEWS ====================

@login_required
def cart(request):
    """Shopping cart page"""
    cart_items = CartItem.objects.filter(user=request.user).select_related(
        'product', 
        'product__category', 
        'product__seller'
    ).prefetch_related('product__images')
    
    # Calculate totals
    subtotal = sum(item.subtotal for item in cart_items)
    shipping = Decimal('50.00') if subtotal > 0 and subtotal < Decimal('500.00') else Decimal('0.00')
    total = subtotal + shipping
    
    # Check for out of stock or low stock items
    warnings = []
    for item in cart_items:
        if not item.product.is_in_stock:
            warnings.append(f"{item.product.name} is out of stock")
        elif item.quantity > item.product.stock_quantity:
            warnings.append(f"Only {item.product.stock_quantity} units of {item.product.name} available")
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
        'warnings': warnings,
        'cart_count': cart_items.count(),
    }
    return render(request, 'shop/cart.html', context)


@login_required
def add_to_cart(request, pk):
    """Add product to cart"""
    if request.method != 'POST':
        return redirect('product_detail', pk=pk)
    
    product = get_object_or_404(Product, pk=pk, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    
    # Validate quantity
    if quantity <= 0:
        messages.error(request, 'Invalid quantity')
        return redirect('product_detail', pk=pk)
    
    # Validate stock
    if not product.is_in_stock:
        messages.error(request, f'{product.name} is currently out of stock')
        return redirect('product_detail', pk=pk)
    
    if quantity > product.stock_quantity:
        messages.error(request, f'Only {product.stock_quantity} items available in stock')
        return redirect('product_detail', pk=pk)
    
    # Get or create cart item
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        # Update existing cart item
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock_quantity:
            cart_item.quantity = product.stock_quantity
            messages.warning(request, f'Maximum available quantity ({product.stock_quantity}) added to cart')
        else:
            cart_item.quantity = new_quantity
            messages.success(request, f'{product.name} quantity updated in cart')
        cart_item.save()
    else:
        messages.success(request, f'✅ {product.name} added to cart')
    
    # Redirect based on request
    next_url = request.POST.get('next', 'cart')
    if next_url == 'product':
        return redirect('product_detail', pk=pk)
    return redirect('cart')


@login_required
def update_cart(request, pk):
    """Update cart item quantity"""
    if request.method != 'POST':
        return redirect('cart')
    
    cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    
    # If quantity is 0 or negative, remove item
    if quantity <= 0:
        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f'{product_name} removed from cart')
        return redirect('cart')
    
    # Validate stock
    if quantity > cart_item.product.stock_quantity:
        messages.error(request, f'Only {cart_item.product.stock_quantity} items available')
        return redirect('cart')
    
    # Update quantity
    cart_item.quantity = quantity
    cart_item.save()
    messages.success(request, 'Cart updated successfully')
    
    return redirect('cart')


@login_required
def remove_from_cart(request, pk):
    """Remove item from cart"""
    if request.method != 'POST':
        return redirect('cart')
    
    cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    
    messages.success(request, f'{product_name} removed from cart')
    return redirect('cart')


@login_required
def clear_cart(request):
    """Clear entire cart"""
    if request.method != 'POST':
        return redirect('cart')
    
    count = CartItem.objects.filter(user=request.user).count()
    CartItem.objects.filter(user=request.user).delete()
    
    messages.success(request, f'Cart cleared ({count} items removed)')
    return redirect('cart')


# ==================== WISHLIST VIEWS ====================

@login_required
def wishlist(request):
    """User's wishlist page"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        'product', 
        'product__category', 
        'product__seller'
    ).prefetch_related('product__images')
    
    context = {
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_items.count(),
    }
    return render(request, 'shop/wishlist.html', context)


@login_required
def add_to_wishlist(request, pk):
    """Add product to wishlist"""
    if request.method != 'POST':
        return redirect('product_detail', pk=pk)
    
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    # Get or create wishlist item
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        messages.success(request, f'❤️ {product.name} added to wishlist')
    else:
        messages.info(request, f'{product.name} is already in your wishlist')
    
    # Get next URL
    next_url = request.POST.get('next', 'product')
    if next_url == 'wishlist':
        return redirect('wishlist')
    return redirect('product_detail', pk=pk)


@login_required
def remove_from_wishlist(request, pk):
    """Remove item from wishlist"""
    if request.method != 'POST':
        return redirect('wishlist')
    
    wishlist_item = get_object_or_404(Wishlist, pk=pk, user=request.user)
    product_name = wishlist_item.product.name
    wishlist_item.delete()
    
    messages.success(request, f'{product_name} removed from wishlist')
    return redirect('wishlist')


@login_required
def toggle_wishlist(request, pk):
    """Toggle product in wishlist (add if not present, remove if present)"""
    if request.method != 'POST':
        return redirect('product_detail', pk=pk)
    
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    
    if wishlist_item:
        # Remove from wishlist
        wishlist_item.delete()
        messages.success(request, f'{product.name} removed from wishlist')
    else:
        # Add to wishlist
        Wishlist.objects.create(user=request.user, product=product)
        messages.success(request, f'❤️ {product.name} added to wishlist')
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'in_wishlist': not bool(wishlist_item)
        })
    
    return redirect('product_detail', pk=pk)


@login_required
def move_all_to_cart(request):
    """Move all wishlist items to cart"""
    if request.method != 'POST':
        return redirect('wishlist')
    
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    moved_count = 0
    out_of_stock = []
    
    for item in wishlist_items:
        # Only move if product is in stock
        if item.product.is_in_stock:
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user,
                product=item.product,
                defaults={'quantity': 1}
            )
            
            if not created:
                # Increment quantity if already in cart
                if cart_item.quantity < item.product.stock_quantity:
                    cart_item.quantity += 1
                    cart_item.save()
            
            moved_count += 1
        else:
            out_of_stock.append(item.product.name)
    
    # Clear wishlist after moving available items
    wishlist_items.delete()
    
    # Show appropriate messages
    if moved_count > 0:
        messages.success(request, f'✅ {moved_count} item(s) moved to cart')
    
    if out_of_stock:
        messages.warning(request, f'⚠️ Out of stock: {", ".join(out_of_stock)}')
    
    return redirect('cart')


@login_required
def clear_wishlist(request):
    """Clear entire wishlist"""
    if request.method != 'POST':
        return redirect('wishlist')
    
    count = Wishlist.objects.filter(user=request.user).count()
    Wishlist.objects.filter(user=request.user).delete()
    
    messages.success(request, f'Wishlist cleared ({count} items removed)')
    return redirect('wishlist')


# ==================== CHECKOUT & PAYMENT VIEWS ====================

@login_required
def checkout(request):
    """Checkout page"""
    cart_items = CartItem.objects.filter(user=request.user).select_related(
        'product'
    ).prefetch_related('product__images')
    
    # Redirect if cart is empty
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('product_list')
    
    # Validate stock availability before checkout
    stock_errors = []
    for item in cart_items:
        if not item.product.is_in_stock:
            stock_errors.append(f"{item.product.name} is out of stock")
        elif item.quantity > item.product.stock_quantity:
            stock_errors.append(f"Only {item.product.stock_quantity} units of {item.product.name} available")
    
    if stock_errors:
        for error in stock_errors:
            messages.error(request, error)
        return redirect('cart')
    
    # Calculate totals
    subtotal = sum(item.subtotal for item in cart_items)
    shipping = Decimal('50.00') if subtotal < Decimal('500.00') else Decimal('0.00')
    total = subtotal + shipping
    
    if request.method == 'POST':
        # Get form data
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        notes = request.POST.get('notes', '').strip()
        payment_method = request.POST.get('payment_method', 'COD')
        
        # Validation
        if not all([full_name, phone, address, city, pincode]):
            messages.error(request, 'Please fill all required fields')
            return render(request, 'shop/checkout.html', {
                'cart_items': cart_items,
                'subtotal': subtotal,
                'shipping': shipping,
                'total': total,
            })
        
        # Validate phone number (basic validation)
        if not phone.isdigit() or len(phone) < 10:
            messages.error(request, 'Please enter a valid phone number')
            return render(request, 'shop/checkout.html', {
                'cart_items': cart_items,
                'subtotal': subtotal,
                'shipping': shipping,
                'total': total,
            })
        
        # Combine address
        full_address = f"{address}, {city}"
        if state:
            full_address += f", {state}"
        full_address += f" - {pincode}"
        
        # Create order
        order = Order.objects.create(
            customer=request.user,
            order_number=f'ORD-{uuid.uuid4().hex[:8].upper()}',
            total_amount=total,
            shipping_address=full_address,
            phone=phone,
            payment_method=payment_method,
            notes=notes,
        )
        
        # Create order items and update stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
                subtotal=item.subtotal
            )
            
            # Reduce stock
            item.product.stock_quantity -= item.quantity
            item.product.save()
        
        # Clear cart
        cart_items.delete()
        
        messages.success(request, f'✅ Order {order.order_number} placed successfully!')
        
        # Redirect to payment or order detail based on payment method
        if payment_method == 'COD':
            # For COD, mark as pending and go to order detail
            order.status = 'confirmed'
            order.save()
            return redirect('order_detail', order_id=order.id)
        else:
            # For online payment, redirect to payment page
            return redirect('payment', order_id=order.id)
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def payment(request, order_id):
    """Payment processing page"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # If already paid, redirect to order detail
    if order.payment_status == 'completed':
        messages.info(request, 'This order has already been paid')
        return redirect('order_detail', order_id=order.id)
    
    if request.method == 'POST':
        # In production, integrate with payment gateway (Razorpay, Stripe, Paytm, etc.)
        # For now, simulate successful payment
        
        payment_type = request.POST.get('payment_type', order.payment_method)
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            transaction_id=f'TXN-{uuid.uuid4().hex[:10].upper()}',
            amount=order.total_amount,
            payment_method=payment_type,
            status='completed',
            payment_date=datetime.now()
        )
        
        # Update order status
        order.payment_status = 'completed'
        order.status = 'confirmed'
        order.save()
        
        messages.success(request, '✅ Payment successful! Your order has been confirmed.')
        return redirect('order_detail', order_id=order.id)
    
    context = {
        'order': order,
    }
    return render(request, 'shop/payment.html', context)


# ==================== ORDER VIEWS ====================

@login_required
def order_list(request):
    """User's order history"""
    orders = Order.objects.filter(customer=request.user).prefetch_related(
        'items__product'
    ).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status and status != 'all':
        orders = orders.filter(status=status)
    
    # Get order statistics
    total_orders = orders.count()
    pending_orders = Order.objects.filter(customer=request.user, status='pending').count()
    completed_orders = Order.objects.filter(customer=request.user, status='delivered').count()
    
    context = {
        'orders': orders,
        'status': status,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
    }
    return render(request, 'shop/order_list.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail and tracking page"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product__images'),
        id=order_id,
        customer=request.user
    )
    
    # Define order status progression
    status_progression = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
    current_index = status_progression.index(order.status) if order.status in status_progression else 0
    
    context = {
        'order': order,
        'status_progression': status_progression,
        'current_status_index': current_index,
    }
    return render(request, 'shop/order_detail.html', context)


@login_required
def cancel_order(request, order_id):
    """Cancel an order"""
    if request.method != 'POST':
        return redirect('order_detail', order_id=order_id)
    
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # Only allow cancellation if order is pending or confirmed
    if order.status in ['pending', 'confirmed']:
        # Restore stock
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
        
        order.status = 'cancelled'
        order.save()
        
        messages.success(request, f'Order {order.order_number} has been cancelled')
    else:
        messages.error(request, 'This order cannot be cancelled')
    
    return redirect('order_detail', order_id=order_id)


# ==================== REVIEW VIEWS ====================

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


# ==================== AUTHENTICATION VIEWS ====================

def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        
        # Validation
        if not all([username, email, password, password2]):
            messages.error(request, 'Please fill all required fields')
            return render(request, 'shop/register.html')
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'shop/register.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'shop/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'shop/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return render(request, 'shop/register.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            address=address
        )
        
        # Create customer profile
        CustomerProfile.objects.create(user=user)
        
        # Login user
        login(request, user)
        messages.success(request, f'🎉 Welcome to Pavan Diary, {username}!')
        return redirect('home')
    
    return render(request, 'shop/register.html')


def user_login(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Get next URL or default to home
            next_url = request.POST.get('next') or request.GET.get('next', 'home')
            
            messages.success(request, f'Welcome back, {user.username}! 🎉')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'shop/login.html')


@login_required
def user_logout(request):
    """User logout"""
    username = request.user.username
    logout(request)
    messages.success(request, f'Goodbye, {username}! Come back soon! 👋')
    return redirect('home')


@login_required
def profile(request):
    """User profile management"""
    # Get user's order statistics
    total_orders = Order.objects.filter(customer=request.user).count()
    total_spent = Order.objects.filter(
        customer=request.user, 
        payment_status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            # Update profile information
            request.user.first_name = request.POST.get('first_name', '').strip()
            request.user.last_name = request.POST.get('last_name', '').strip()
            request.user.email = request.POST.get('email', '').strip()
            request.user.phone = request.POST.get('phone', '').strip()
            request.user.address = request.POST.get('address', '').strip()
            
            # Validate email
            if User.objects.exclude(pk=request.user.pk).filter(email=request.user.email).exists():
                messages.error(request, 'Email already in use by another account')
                return redirect('profile')
            
            request.user.save()
            messages.success(request, '✅ Profile updated successfully')
        
        elif form_type == 'password':
            # Change password
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            # Validation
            if not request.user.check_password(old_password):
                messages.error(request, 'Current password is incorrect')
            elif new_password1 != new_password2:
                messages.error(request, 'New passwords do not match')
            elif len(new_password1) < 8:
                messages.error(request, 'Password must be at least 8 characters long')
            else:
                # Update password
                request.user.set_password(new_password1)
                request.user.save()
                
                # Keep user logged in after password change
                update_session_auth_hash(request, request.user)
                
                messages.success(request, '🔒 Password changed successfully')
        
        return redirect('profile')
    
    context = {
        'total_orders': total_orders,
        'total_spent': total_spent,
    }
    return render(request, 'shop/profile.html', context)


def password_reset(request):
    """Password reset request"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        try:
            user = User.objects.get(email=email)
            # In production, send actual email with reset link using Django's password reset
            # For now, just show success message
            messages.success(request, '📧 Password reset link has been sent to your email')
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(request, '📧 If an account exists with this email, a password reset link has been sent')
        
        return redirect('login')
    
    return render(request, 'shop/password_reset.html')


# ==================== CATEGORY VIEW ====================

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
    return render(request, 'shop/category_products.html', context)



# """
# Pavan Diary E-commerce - Views
# Complete view functions for all features
# """

# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.db.models import Q, Avg
# from django.http import JsonResponse
# from django.views.decorators.http import require_POST
# from .models import (
#     User, CustomerProfile, SellerProfile, Category, Product, 
#     ProductImage, Order, OrderItem, CartItem, Payment, 
#     Review, ProductListing, Wishlist
# )
# from decimal import Decimal
# import uuid
# from datetime import datetime


# # ==================== PUBLIC VIEWS ====================

# def home(request):
#     """Homepage with featured products and categories"""
#     featured_products = Product.objects.filter(
#         is_active=True,
#         listing__featured=True
#     ).select_related('category', 'seller', 'listing')[:8]
    
#     categories = Category.objects.filter(is_active=True)
    
#     context = {
#         'featured_products': featured_products,
#         'categories': categories,
#     }
#     return render(request, 'shop/home.html', context)


# def product_list(request):
#     """List all products with filters and search"""
#     products = Product.objects.filter(is_active=True).select_related('category', 'seller', 'listing')
    
#     # Search functionality
#     query = request.GET.get('q')
#     if query:
#         products = products.filter(
#             Q(name__icontains=query) | 
#             Q(description__icontains=query) |
#             Q(category__name__icontains=query)
#         )
    
#     # Category filter
#     category_id = request.GET.get('category')
#     if category_id:
#         products = products.filter(category_id=category_id)
    
#     # Organic filter
#     organic = request.GET.get('organic')
#     if organic == 'true':
#         products = products.filter(is_organic=True)
    
#     # Price range filter
#     price_range = request.GET.get('price')
#     if price_range:
#         if price_range == '0-100':
#             products = products.filter(price__lt=100)
#         elif price_range == '100-200':
#             products = products.filter(price__gte=100, price__lt=200)
#         elif price_range == '200-500':
#             products = products.filter(price__gte=200, price__lt=500)
#         elif price_range == '500-':
#             products = products.filter(price__gte=500)
    
#     # Sorting
#     sort = request.GET.get('sort', '-created_at')
#     valid_sorts = ['price', '-price', 'name', '-name', 'rating', '-rating', 'created_at', '-created_at']
#     if sort in valid_sorts:
#         products = products.order_by(sort)
#     else:
#         products = products.order_by('-created_at')
    
#     # Get all categories for filter sidebar
#     categories = Category.objects.filter(is_active=True)
    
#     context = {
#         'products': products,
#         'categories': categories,
#     }
#     return render(request, 'shop/product_list.html', context)


# def product_detail(request, pk):
#     """Product detail page with reviews and related products"""
#     product = get_object_or_404(
#         Product.objects.select_related('category', 'seller', 'listing'),
#         pk=pk,
#         is_active=True
#     )
    
#     # Increment view count
#     if hasattr(product, 'listing'):
#         product.listing.view_count += 1
#         product.listing.save()
    
#     # Get related products from same category
#     related_products = Product.objects.filter(
#         category=product.category,
#         is_active=True
#     ).exclude(pk=pk).select_related('category', 'seller')[:4]
    
#     # Get product reviews
#     reviews = product.reviews.select_related('user').order_by('-created_at')
    
#     context = {
#         'product': product,
#         'related_products': related_products,
#         'reviews': reviews,
#     }
#     return render(request, 'shop/product_detail.html', context)


# # ==================== CART VIEWS ====================

# @login_required
# def cart(request):
#     """Shopping cart page"""
#     cart_items = CartItem.objects.filter(user=request.user).select_related(
#         'product', 
#         'product__category', 
#         'product__seller'
#     )
    
#     # Calculate total
#     total = sum(item.subtotal for item in cart_items)
    
#     context = {
#         'cart_items': cart_items,
#         'total': total,
#     }
#     return render(request, 'shop/cart.html', context)


# @login_required
# def add_to_cart(request, pk):
#     """Add product to cart"""
#     if request.method != 'POST':
#         return redirect('product_detail', pk=pk)
    
#     product = get_object_or_404(Product, pk=pk, is_active=True)
#     quantity = int(request.POST.get('quantity', 1))
    
#     # Validate stock
#     if quantity > product.stock_quantity:
#         messages.error(request, f'Only {product.stock_quantity} items available in stock')
#         return redirect('product_detail', pk=pk)
    
#     # Get or create cart item
#     cart_item, created = CartItem.objects.get_or_create(
#         user=request.user,
#         product=product,
#         defaults={'quantity': quantity}
#     )
    
#     if not created:
#         # Update existing cart item
#         new_quantity = cart_item.quantity + quantity
#         if new_quantity > product.stock_quantity:
#             cart_item.quantity = product.stock_quantity
#             messages.warning(request, f'Maximum available quantity ({product.stock_quantity}) added to cart')
#         else:
#             cart_item.quantity = new_quantity
#             messages.success(request, f'{product.name} quantity updated in cart')
#         cart_item.save()
#     else:
#         messages.success(request, f'{product.name} added to cart')
    
#     return redirect('cart')


# @login_required
# def update_cart(request, pk):
#     """Update cart item quantity"""
#     if request.method != 'POST':
#         return redirect('cart')
    
#     cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
#     quantity = int(request.POST.get('quantity', 1))
    
#     # If quantity is 0 or negative, remove item
#     if quantity <= 0:
#         product_name = cart_item.product.name
#         cart_item.delete()
#         messages.success(request, f'{product_name} removed from cart')
#         return redirect('cart')
    
#     # Validate stock
#     if quantity > cart_item.product.stock_quantity:
#         messages.error(request, f'Only {cart_item.product.stock_quantity} items available')
#         return redirect('cart')
    
#     # Update quantity
#     cart_item.quantity = quantity
#     cart_item.save()
#     messages.success(request, 'Cart updated successfully')
    
#     return redirect('cart')


# @login_required
# def remove_from_cart(request, pk):
#     """Remove item from cart"""
#     if request.method != 'POST':
#         return redirect('cart')
    
#     cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
#     product_name = cart_item.product.name
#     cart_item.delete()
    
#     messages.success(request, f'{product_name} removed from cart')
#     return redirect('cart')


# # ==================== WISHLIST VIEWS ====================

# @login_required
# def wishlist(request):
#     """User's wishlist page"""
#     wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
#         'product', 
#         'product__category', 
#         'product__seller'
#     )
    
#     context = {
#         'wishlist_items': wishlist_items,
#     }
#     return render(request, 'shop/wishlist.html', context)


# @login_required
# def add_to_wishlist(request, pk):
#     """Add product to wishlist"""
#     if request.method != 'POST':
#         return redirect('product_detail', pk=pk)
    
#     product = get_object_or_404(Product, pk=pk, is_active=True)
    
#     # Get or create wishlist item
#     wishlist_item, created = Wishlist.objects.get_or_create(
#         user=request.user,
#         product=product
#     )
    
#     if created:
#         messages.success(request, f'{product.name} added to wishlist ❤️')
#     else:
#         messages.info(request, f'{product.name} is already in your wishlist')
    
#     return redirect('product_detail', pk=pk)


# @login_required
# def remove_from_wishlist(request, pk):
#     """Remove item from wishlist"""
#     if request.method != 'POST':
#         return redirect('wishlist')
    
#     wishlist_item = get_object_or_404(Wishlist, pk=pk, user=request.user)
#     product_name = wishlist_item.product.name
#     wishlist_item.delete()
    
#     messages.success(request, f'{product_name} removed from wishlist')
#     return redirect('wishlist')


# @login_required
# def move_all_to_cart(request):
#     """Move all wishlist items to cart"""
#     if request.method != 'POST':
#         return redirect('wishlist')
    
#     wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
#     moved_count = 0
#     out_of_stock = []
    
#     for item in wishlist_items:
#         # Only move if product is in stock
#         if item.product.is_in_stock:
#             cart_item, created = CartItem.objects.get_or_create(
#                 user=request.user,
#                 product=item.product,
#                 defaults={'quantity': 1}
#             )
            
#             if not created:
#                 # Increment quantity if already in cart
#                 if cart_item.quantity < item.product.stock_quantity:
#                     cart_item.quantity += 1
#                     cart_item.save()
            
#             moved_count += 1
#         else:
#             out_of_stock.append(item.product.name)
    
#     # Clear wishlist after moving available items
#     wishlist_items.delete()
    
#     # Show appropriate messages
#     if moved_count > 0:
#         messages.success(request, f'{moved_count} item(s) moved to cart')
    
#     if out_of_stock:
#         messages.warning(request, f'Out of stock: {", ".join(out_of_stock)}')
    
#     return redirect('cart')


# @login_required
# def clear_wishlist(request):
#     """Clear entire wishlist"""
#     if request.method != 'POST':
#         return redirect('wishlist')
    
#     count = Wishlist.objects.filter(user=request.user).count()
#     Wishlist.objects.filter(user=request.user).delete()
    
#     messages.success(request, f'Wishlist cleared ({count} items removed)')
#     return redirect('wishlist')


# # ==================== CHECKOUT & PAYMENT VIEWS ====================

# @login_required
# def checkout(request):
#     """Checkout page"""
#     cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    
#     # Redirect if cart is empty
#     if not cart_items.exists():
#         messages.warning(request, 'Your cart is empty')
#         return redirect('product_list')
    
#     # Calculate total
#     total = sum(item.subtotal for item in cart_items)
    
#     if request.method == 'POST':
#         # Get form data
#         full_name = request.POST.get('full_name', '')
#         phone = request.POST.get('phone')
#         address = request.POST.get('address')
#         city = request.POST.get('city', '')
#         pincode = request.POST.get('pincode', '')
#         notes = request.POST.get('notes', '')
#         payment_method = request.POST.get('payment_method', 'COD')
        
#         # Combine address
#         full_address = f"{address}, {city} - {pincode}"
        
#         # Create order
#         order = Order.objects.create(
#             customer=request.user,
#             order_number=f'ORD-{uuid.uuid4().hex[:8].upper()}',
#             total_amount=total,
#             shipping_address=full_address,
#             phone=phone,
#             payment_method=payment_method,
#             notes=notes,
#         )
        
#         # Create order items and update stock
#         for item in cart_items:
#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 quantity=item.quantity,
#                 price=item.product.price,
#                 subtotal=item.subtotal
#             )
            
#             # Reduce stock
#             item.product.stock_quantity -= item.quantity
#             item.product.save()
        
#         # Clear cart
#         cart_items.delete()
        
#         messages.success(request, f'Order {order.order_number} placed successfully!')
        
#         # Redirect to payment
#         return redirect('payment', order_id=order.id)
    
#     context = {
#         'cart_items': cart_items,
#         'total': total,
#     }
#     return render(request, 'shop/checkout.html', context)


# @login_required
# def payment(request, order_id):
#     """Payment processing page"""
#     order = get_object_or_404(Order, id=order_id, customer=request.user)
    
#     if request.method == 'POST':
#         # In production, integrate with payment gateway (Razorpay, Stripe, etc.)
#         # For now, simulate successful payment
        
#         payment_type = request.POST.get('payment_type', order.payment_method)
        
#         # Create payment record
#         payment = Payment.objects.create(
#             order=order,
#             transaction_id=f'TXN-{uuid.uuid4().hex[:10].upper()}',
#             amount=order.total_amount,
#             payment_method=payment_type,
#             status='completed',
#             payment_date=datetime.now()
#         )
        
#         # Update order status
#         order.payment_status = 'completed'
#         order.status = 'confirmed'
#         order.save()
        
#         messages.success(request, '✅ Payment successful! Your order has been confirmed.')
#         return redirect('order_detail', order_id=order.id)
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'shop/payment.html', context)


# # ==================== ORDER VIEWS ====================

# @login_required
# def order_list(request):
#     """User's order history"""
#     orders = Order.objects.filter(customer=request.user).prefetch_related('items').order_by('-created_at')
    
#     # Filter by status
#     status = request.GET.get('status')
#     if status and status != 'all':
#         orders = orders.filter(status=status)
    
#     context = {
#         'orders': orders,
#     }
#     return render(request, 'shop/order_list.html', context)


# @login_required
# def order_detail(request, order_id):
#     """Order detail and tracking page"""
#     order = get_object_or_404(
#         Order.objects.prefetch_related('items__product'),
#         id=order_id,
#         customer=request.user
#     )
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'shop/order_detail.html', context)


# # ==================== AUTHENTICATION VIEWS ====================

# def register(request):
#     """User registration"""
#     if request.user.is_authenticated:
#         return redirect('home')
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         password2 = request.POST.get('password2')
#         first_name = request.POST.get('first_name', '')
#         last_name = request.POST.get('last_name', '')
#         phone = request.POST.get('phone', '')
#         address = request.POST.get('address', '')
        
#         # Validation
#         if password != password2:
#             messages.error(request, 'Passwords do not match')
#             return render(request, 'shop/register.html')
        
#         if len(password) < 8:
#             messages.error(request, 'Password must be at least 8 characters long')
#             return render(request, 'shop/register.html')
        
#         if User.objects.filter(username=username).exists():
#             messages.error(request, 'Username already exists')
#             return render(request, 'shop/register.html')
        
#         if User.objects.filter(email=email).exists():
#             messages.error(request, 'Email already registered')
#             return render(request, 'shop/register.html')
        
#         # Create user
#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password,
#             first_name=first_name,
#             last_name=last_name,
#             phone=phone,
#             address=address
#         )
        
#         # Create customer profile
#         CustomerProfile.objects.create(user=user)
        
#         # Login user
#         login(request, user)
#         messages.success(request, f'Welcome to Pavan Diary, {username}! 🥛')
#         return redirect('home')
    
#     return render(request, 'shop/register.html')


# def user_login(request):
#     """User login"""
#     if request.user.is_authenticated:
#         return redirect('home')
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
        
#         # Authenticate user
#         user = authenticate(request, username=username, password=password)
        
#         if user is not None:
#             login(request, user)
            
#             # Get next URL or default to home
#             next_url = request.POST.get('next') or request.GET.get('next', 'home')
            
#             messages.success(request, f'Welcome back, {user.username}! 🎉')
#             return redirect(next_url)
#         else:
#             messages.error(request, 'Invalid username or password')
    
#     return render(request, 'shop/login.html')


# @login_required
# def user_logout(request):
#     """User logout"""
#     username = request.user.username
#     logout(request)
#     messages.success(request, f'Goodbye, {username}! Come back soon! 👋')
#     return redirect('home')


# @login_required
# def profile(request):
#     """User profile management"""
#     if request.method == 'POST':
#         form_type = request.POST.get('form_type')
        
#         if form_type == 'profile':
#             # Update profile information
#             request.user.first_name = request.POST.get('first_name', '')
#             request.user.last_name = request.POST.get('last_name', '')
#             request.user.email = request.POST.get('email')
#             request.user.phone = request.POST.get('phone', '')
#             request.user.address = request.POST.get('address', '')
#             request.user.save()
            
#             messages.success(request, 'Profile updated successfully ✅')
        
#         elif form_type == 'password':
#             # Change password
#             old_password = request.POST.get('old_password')
#             new_password1 = request.POST.get('new_password1')
#             new_password2 = request.POST.get('new_password2')
            
#             # Validation
#             if not request.user.check_password(old_password):
#                 messages.error(request, 'Current password is incorrect')
#             elif new_password1 != new_password2:
#                 messages.error(request, 'New passwords do not match')
#             elif len(new_password1) < 8:
#                 messages.error(request, 'Password must be at least 8 characters long')
#             else:
#                 # Update password
#                 request.user.set_password(new_password1)
#                 request.user.save()
                
#                 # Keep user logged in after password change
#                 update_session_auth_hash(request, request.user)
                
#                 messages.success(request, 'Password changed successfully 🔒')
        
#         return redirect('profile')
    
#     return render(request, 'shop/profile.html')


# def password_reset(request):
#     """Password reset request"""
#     if request.method == 'POST':
#         email = request.POST.get('email')
        
#         try:
#             user = User.objects.get(email=email)
#             # In production, send actual email with reset link
#             # For now, just show success message
#             messages.success(request, 'Password reset link has been sent to your email 📧')
#         except User.DoesNotExist:
#             messages.error(request, 'No account found with this email address')
        
#         return redirect('login')
    
#     return render(request, 'shop/password_reset.html')




# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth import login, authenticate, logout
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.db.models import Q, Avg
# from django.http import JsonResponse
# from django.views.decorators.http import require_POST
# from .models import *
# from decimal import Decimal
# import uuid
# from datetime import datetime


# def home(request):
#     """Homepage with featured products"""
#     featured_products = Product.objects.filter(
#         is_active=True,
#         listing__featured=True
#     ).select_related('category', 'seller')[:8]
    
#     categories = Category.objects.filter(is_active=True)
    
#     context = {
#         'featured_products': featured_products,
#         'categories': categories,
#     }
#     return render(request, 'shop/home.html', context)


# def product_list(request):
#     """List all products with filters"""
#     products = Product.objects.filter(is_active=True).select_related('category', 'seller')
    
#     # Search
#     query = request.GET.get('q')
#     if query:
#         products = products.filter(
#             Q(name__icontains=query) | 
#             Q(description__icontains=query)
#         )
    
#     # Category filter
#     category_id = request.GET.get('category')
#     if category_id:
#         products = products.filter(category_id=category_id)
    
#     # Organic filter
#     organic = request.GET.get('organic')
#     if organic == 'true':
#         products = products.filter(is_organic=True)
    
#     # Sort
#     sort = request.GET.get('sort', '-created_at')
#     products = products.order_by(sort)
    
#     categories = Category.objects.filter(is_active=True)
    
#     context = {
#         'products': products,
#         'categories': categories,
#     }
#     return render(request, 'shop/product_list.html', context)


# def product_detail(request, pk):
#     """Product detail page"""
#     product = get_object_or_404(
#         Product.objects.select_related('category', 'seller'),
#         pk=pk,
#         is_active=True
#     )
    
#     # Increment view count
#     if hasattr(product, 'listing'):
#         product.listing.view_count += 1
#         product.listing.save()
    
#     # Get related products
#     related_products = Product.objects.filter(
#         category=product.category,
#         is_active=True
#     ).exclude(pk=pk)[:4]
    
#     # Get reviews
#     reviews = product.reviews.select_related('user').order_by('-created_at')
    
#     context = {
#         'product': product,
#         'related_products': related_products,
#         'reviews': reviews,
#     }
#     return render(request, 'shop/product_detail.html', context)


# @login_required
# def add_to_cart(request, pk):
#     """Add product to cart"""
#     product = get_object_or_404(Product, pk=pk, is_active=True)
#     quantity = int(request.POST.get('quantity', 1))
    
#     if quantity > product.stock_quantity:
#         messages.error(request, 'Not enough stock available')
#         return redirect('product_detail', pk=pk)
    
#     cart_item, created = CartItem.objects.get_or_create(
#         user=request.user,
#         product=product,
#         defaults={'quantity': quantity}
#     )
    
#     if not created:
#         cart_item.quantity += quantity
#         cart_item.save()
    
#     messages.success(request, f'{product.name} added to cart')
#     return redirect('cart')


# @login_required
# def cart(request):
#     """Shopping cart page"""
#     cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    
#     total = sum(item.subtotal for item in cart_items)
    
#     context = {
#         'cart_items': cart_items,
#         'total': total,
#     }
#     return render(request, 'shop/cart.html', context)


# @login_required
# @require_POST
# def update_cart(request, pk):
#     """Update cart item quantity"""
#     cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
#     quantity = int(request.POST.get('quantity', 1))
    
#     if quantity <= 0:
#         cart_item.delete()
#         return JsonResponse({'status': 'deleted'})
    
#     if quantity > cart_item.product.stock_quantity:
#         return JsonResponse({'status': 'error', 'message': 'Not enough stock'})
    
#     cart_item.quantity = quantity
#     cart_item.save()
    
#     return JsonResponse({
#         'status': 'success',
#         'subtotal': str(cart_item.subtotal)
#     })


# @login_required
# def remove_from_cart(request, pk):
#     """Remove item from cart"""
#     cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
#     cart_item.delete()
#     messages.success(request, 'Item removed from cart')
#     return redirect('cart')


# @login_required
# def checkout(request):
#     """Checkout page"""
#     cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    
#     if not cart_items:
#         messages.warning(request, 'Your cart is empty')
#         return redirect('product_list')
    
#     total = sum(item.subtotal for item in cart_items)
    
#     if request.method == 'POST':
#         # Create order
#         order = Order.objects.create(
#             customer=request.user,
#             order_number=f'ORD-{uuid.uuid4().hex[:8].upper()}',
#             total_amount=total,
#             shipping_address=request.POST.get('address'),
#             phone=request.POST.get('phone'),
#             payment_method=request.POST.get('payment_method'),
#             notes=request.POST.get('notes', ''),
#         )
        
#         # Create order items
#         for item in cart_items:
#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 quantity=item.quantity,
#                 price=item.product.price,
#                 subtotal=item.subtotal
#             )
            
#             # Update stock
#             item.product.stock_quantity -= item.quantity
#             item.product.save()
        
#         # Clear cart
#         cart_items.delete()
        
#         # Redirect to payment
#         return redirect('payment', order_id=order.id)
    
#     context = {
#         'cart_items': cart_items,
#         'total': total,
#     }
#     return render(request, 'shop/checkout.html', context)


# @login_required
# def payment(request, order_id):
#     """Payment processing page"""
#     order = get_object_or_404(Order, id=order_id, customer=request.user)
    
#     if request.method == 'POST':
#         # Simulate payment processing
#         # In production, integrate with real payment gateway like Stripe, Razorpay, etc.
        
#         payment = Payment.objects.create(
#             order=order,
#             transaction_id=f'TXN-{uuid.uuid4().hex[:10].upper()}',
#             amount=order.total_amount,
#             payment_method=order.payment_method,
#             status='completed',
#             payment_date=datetime.now()
#         )
        
#         order.payment_status = 'completed'
#         order.status = 'confirmed'
#         order.save()
        
#         messages.success(request, 'Payment successful! Your order has been confirmed.')
#         return redirect('order_detail', order_id=order.id)
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'shop/payment.html', context)


# @login_required
# def order_list(request):
#     """User's order history"""
#     orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
#     context = {
#         'orders': orders,
#     }
#     return render(request, 'shop/order_list.html', context)


# @login_required
# def order_detail(request, order_id):
#     """Order detail page"""
#     order = get_object_or_404(
#         Order.objects.prefetch_related('items__product'),
#         id=order_id,
#         customer=request.user
#     )
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'shop/order_detail.html', context)


# def register(request):
#     """User registration"""
#     if request.user.is_authenticated:
#         return redirect('home')
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         phone = request.POST.get('phone')
#         address = request.POST.get('address')
        
#         if User.objects.filter(username=username).exists():
#             messages.error(request, 'Username already exists')
#             return render(request, 'shop/register.html')
        
#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password,
#             phone=phone,
#             address=address
#         )
        
#         # Create customer profile
#         CustomerProfile.objects.create(user=user)
        
#         login(request, user)
#         messages.success(request, 'Registration successful!')
#         return redirect('home')
    
#     return render(request, 'shop/register.html')


# def user_login(request):
#     """User login"""
#     if request.user.is_authenticated:
#         return redirect('home')
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
        
#         user = authenticate(request, username=username, password=password)
        
#         if user:
#             login(request, user)
#             next_url = request.GET.get('next', 'home')
#             return redirect(next_url)
#         else:
#             messages.error(request, 'Invalid credentials')
    
#     return render(request, 'shop/login.html')


# @login_required
# def user_logout(request):
#     """User logout"""
#     logout(request)
#     messages.success(request, 'Logged out successfully')
#     return redirect('home')


# @login_required
# def profile(request):
#     """User profile page"""
#     if request.method == 'POST':
#         form_type = request.POST.get('form_type')
        
#         if form_type == 'profile':
#             request.user.first_name = request.POST.get('first_name', '')
#             request.user.last_name = request.POST.get('last_name', '')
#             request.user.email = request.POST.get('email')
#             request.user.phone = request.POST.get('phone')
#             request.user.address = request.POST.get('address')
#             request.user.save()
            
#             messages.success(request, 'Profile updated successfully')
        
#         elif form_type == 'password':
#             from django.contrib.auth import update_session_auth_hash
#             old_password = request.POST.get('old_password')
#             new_password1 = request.POST.get('new_password1')
#             new_password2 = request.POST.get('new_password2')
            
#             if not request.user.check_password(old_password):
#                 messages.error(request, 'Current password is incorrect')
#             elif new_password1 != new_password2:
#                 messages.error(request, 'New passwords do not match')
#             elif len(new_password1) < 8:
#                 messages.error(request, 'Password must be at least 8 characters')
#             else:
#                 request.user.set_password(new_password1)
#                 request.user.save()
#                 update_session_auth_hash(request, request.user)
#                 messages.success(request, 'Password changed successfully')
        
#         return redirect('profile')
    
#     return render(request, 'shop/profile.html')


# def password_reset(request):
#     """Password reset request"""
#     if request.method == 'POST':
#         email = request.POST.get('email')
#         try:
#             user = User.objects.get(email=email)
#             # In production, send actual email
#             messages.success(request, 'Password reset link has been sent to your email')
#         except User.DoesNotExist:
#             messages.error(request, 'No account found with this email')
#         return redirect('login')
    
#     return render(request, 'shop/password_reset.html')


# @login_required
# def wishlist(request):
#     """User's wishlist"""
#     wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
#     context = {
#         'wishlist_items': wishlist_items,
#     }
#     return render(request, 'shop/wishlist.html', context)


# @login_required
# def add_to_wishlist(request, pk):
#     """Add product to wishlist"""
#     product = get_object_or_404(Product, pk=pk, is_active=True)
    
#     wishlist_item, created = Wishlist.objects.get_or_create(
#         user=request.user,
#         product=product
#     )
    
#     if created:
#         messages.success(request, f'{product.name} added to wishlist')
#     else:
#         messages.info(request, f'{product.name} is already in your wishlist')
    
#     return redirect('product_detail', pk=pk)


# @login_required
# def remove_from_wishlist(request, pk):
#     """Remove item from wishlist"""
#     wishlist_item = get_object_or_404(Wishlist, pk=pk, user=request.user)
#     product_name = wishlist_item.product.name
#     wishlist_item.delete()
    
#     messages.success(request, f'{product_name} removed from wishlist')
#     return redirect('wishlist')


# @login_required
# def move_all_to_cart(request):
#     """Move all wishlist items to cart"""
#     wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
#     moved_count = 0
#     for item in wishlist_items:
#         if item.product.is_in_stock:
#             cart_item, created = CartItem.objects.get_or_create(
#                 user=request.user,
#                 product=item.product,
#                 defaults={'quantity': 1}
#             )
#             if not created:
#                 cart_item.quantity += 1
#                 cart_item.save()
#             moved_count += 1
    
#     # Clear wishlist after moving
#     wishlist_items.delete()
    
#     messages.success(request, f'{moved_count} item(s) moved to cart')
#     return redirect('cart')


# @login_required
# def clear_wishlist(request):
#     """Clear entire wishlist"""
#     if request.method == 'POST':
#         Wishlist.objects.filter(user=request.user).delete()
#         messages.success(request, 'Wishlist cleared')
#     return redirect('wishlist')






# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth import login, authenticate, logout
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.db.models import Q, Avg
# from django.http import JsonResponse
# from django.views.decorators.http import require_POST
# from .models import *
# from decimal import Decimal
# import uuid
# from datetime import datetime


# def home(request):
#     """Homepage with featured products"""
#     featured_products = Product.objects.filter(
#         is_active=True,
#         listing__featured=True
#     ).select_related('category', 'seller')[:8]
    
#     categories = Category.objects.filter(is_active=True)
    
#     context = {
#         'featured_products': featured_products,
#         'categories': categories,
#     }
#     return render(request, 'shop/home.html', context)


# def product_list(request):
#     """List all products with filters"""
#     products = Product.objects.filter(is_active=True).select_related('category', 'seller')
    
#     # Search
#     query = request.GET.get('q')
#     if query:
#         products = products.filter(
#             Q(name__icontains=query) | 
#             Q(description__icontains=query)
#         )
    
#     # Category filter
#     category_id = request.GET.get('category')
#     if category_id:
#         products = products.filter(category_id=category_id)
    
#     # Organic filter
#     organic = request.GET.get('organic')
#     if organic == 'true':
#         products = products.filter(is_organic=True)
    
#     # Sort
#     sort = request.GET.get('sort', '-created_at')
#     products = products.order_by(sort)
    
#     categories = Category.objects.filter(is_active=True)
    
#     context = {
#         'products': products,
#         'categories': categories,
#     }
#     return render(request, 'shop/product_list.html', context)


# def product_detail(request, pk):
#     """Product detail page"""
#     product = get_object_or_404(
#         Product.objects.select_related('category', 'seller'),
#         pk=pk,
#         is_active=True
#     )
    
#     # Increment view count
#     if hasattr(product, 'listing'):
#         product.listing.view_count += 1
#         product.listing.save()
    
#     # Get related products
#     related_products = Product.objects.filter(
#         category=product.category,
#         is_active=True
#     ).exclude(pk=pk)[:4]
    
#     # Get reviews
#     reviews = product.reviews.select_related('user').order_by('-created_at')
    
#     context = {
#         'product': product,
#         'related_products': related_products,
#         'reviews': reviews,
#     }
#     return render(request, 'shop/product_detail.html', context)


# @login_required
# def add_to_cart(request, pk):
#     """Add product to cart"""
#     product = get_object_or_404(Product, pk=pk, is_active=True)
#     quantity = int(request.POST.get('quantity', 1))
    
#     if quantity > product.stock_quantity:
#         messages.error(request, 'Not enough stock available')
#         return redirect('product_detail', pk=pk)
    
#     cart_item, created = CartItem.objects.get_or_create(
#         user=request.user,
#         product=product,
#         defaults={'quantity': quantity}
#     )
    
#     if not created:
#         cart_item.quantity += quantity
#         cart_item.save()
    
#     messages.success(request, f'{product.name} added to cart')
#     return redirect('cart')


# @login_required
# def cart(request):
#     """Shopping cart page"""
#     cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    
#     total = sum(item.subtotal for item in cart_items)
    
#     context = {
#         'cart_items': cart_items,
#         'total': total,
#     }
#     return render(request, 'shop/cart.html', context)


# @login_required
# @require_POST
# def update_cart(request, pk):
#     """Update cart item quantity"""
#     cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
#     quantity = int(request.POST.get('quantity', 1))
    
#     if quantity <= 0:
#         cart_item.delete()
#         return JsonResponse({'status': 'deleted'})
    
#     if quantity > cart_item.product.stock_quantity:
#         return JsonResponse({'status': 'error', 'message': 'Not enough stock'})
    
#     cart_item.quantity = quantity
#     cart_item.save()
    
#     return JsonResponse({
#         'status': 'success',
#         'subtotal': str(cart_item.subtotal)
#     })


# @login_required
# def remove_from_cart(request, pk):
#     """Remove item from cart"""
#     cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
#     cart_item.delete()
#     messages.success(request, 'Item removed from cart')
#     return redirect('cart')


# @login_required
# def checkout(request):
#     """Checkout page"""
#     cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    
#     if not cart_items:
#         messages.warning(request, 'Your cart is empty')
#         return redirect('product_list')
    
#     total = sum(item.subtotal for item in cart_items)
    
#     if request.method == 'POST':
#         # Create order
#         order = Order.objects.create(
#             customer=request.user,
#             order_number=f'ORD-{uuid.uuid4().hex[:8].upper()}',
#             total_amount=total,
#             shipping_address=request.POST.get('address'),
#             phone=request.POST.get('phone'),
#             payment_method=request.POST.get('payment_method'),
#             notes=request.POST.get('notes', ''),
#         )
        
#         # Create order items
#         for item in cart_items:
#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 quantity=item.quantity,
#                 price=item.product.price,
#                 subtotal=item.subtotal
#             )
            
#             # Update stock
#             item.product.stock_quantity -= item.quantity
#             item.product.save()
        
#         # Clear cart
#         cart_items.delete()
        
#         # Redirect to payment
#         return redirect('payment', order_id=order.id)
    
#     context = {
#         'cart_items': cart_items,
#         'total': total,
#     }
#     return render(request, 'shop/checkout.html', context)


# @login_required
# def payment(request, order_id):
#     """Payment processing page"""
#     order = get_object_or_404(Order, id=order_id, customer=request.user)
    
#     if request.method == 'POST':
#         # Simulate payment processing
#         # In production, integrate with real payment gateway like Stripe, Razorpay, etc.
        
#         payment = Payment.objects.create(
#             order=order,
#             transaction_id=f'TXN-{uuid.uuid4().hex[:10].upper()}',
#             amount=order.total_amount,
#             payment_method=order.payment_method,
#             status='completed',
#             payment_date=datetime.now()
#         )
        
#         order.payment_status = 'completed'
#         order.status = 'confirmed'
#         order.save()
        
#         messages.success(request, 'Payment successful! Your order has been confirmed.')
#         return redirect('order_detail', order_id=order.id)
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'shop/payment.html', context)


# @login_required
# def order_list(request):
#     """User's order history"""
#     orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
#     context = {
#         'orders': orders,
#     }
#     return render(request, 'shop/order_list.html', context)


# @login_required
# def order_detail(request, order_id):
#     """Order detail page"""
#     order = get_object_or_404(
#         Order.objects.prefetch_related('items__product'),
#         id=order_id,
#         customer=request.user
#     )
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'shop/order_detail.html', context)


# def register(request):
#     """User registration"""
#     if request.user.is_authenticated:
#         return redirect('home')
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         phone = request.POST.get('phone')
#         address = request.POST.get('address')
        
#         if User.objects.filter(username=username).exists():
#             messages.error(request, 'Username already exists')
#             return render(request, 'shop/register.html')
        
#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password,
#             phone=phone,
#             address=address
#         )
        
#         # Create customer profile
#         CustomerProfile.objects.create(user=user)
        
#         login(request, user)
#         messages.success(request, 'Registration successful!')
#         return redirect('home')
    
#     return render(request, 'shop/register.html')


# def user_login(request):
#     """User login"""
#     if request.user.is_authenticated:
#         return redirect('home')
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
        
#         user = authenticate(request, username=username, password=password)
        
#         if user:
#             login(request, user)
#             next_url = request.GET.get('next', 'home')
#             return redirect(next_url)
#         else:
#             messages.error(request, 'Invalid credentials')
    
#     return render(request, 'shop/login.html')


# @login_required
# def user_logout(request):
#     """User logout"""
#     logout(request)
#     messages.success(request, 'Logged out successfully')
#     return redirect('home')


# @login_required
# def profile(request):
#     """User profile page"""
#     if request.method == 'POST':
#         form_type = request.POST.get('form_type')
        
#         if form_type == 'profile':
#             request.user.first_name = request.POST.get('first_name', '')
#             request.user.last_name = request.POST.get('last_name', '')
#             request.user.email = request.POST.get('email')
#             request.user.phone = request.POST.get('phone')
#             request.user.address = request.POST.get('address')
#             request.user.save()
            
#             messages.success(request, 'Profile updated successfully')
        
#         elif form_type == 'password':
#             from django.contrib.auth import update_session_auth_hash
#             old_password = request.POST.get('old_password')
#             new_password1 = request.POST.get('new_password1')
#             new_password2 = request.POST.get('new_password2')
            
#             if not request.user.check_password(old_password):
#                 messages.error(request, 'Current password is incorrect')
#             elif new_password1 != new_password2:
#                 messages.error(request, 'New passwords do not match')
#             elif len(new_password1) < 8:
#                 messages.error(request, 'Password must be at least 8 characters')
#             else:
#                 request.user.set_password(new_password1)
#                 request.user.save()
#                 update_session_auth_hash(request, request.user)
#                 messages.success(request, 'Password changed successfully')
        
#         return redirect('profile')
    
#     return render(request, 'shop/profile.html')


# def password_reset(request):
#     """Password reset request"""
#     if request.method == 'POST':
#         email = request.POST.get('email')
#         try:
#             user = User.objects.get(email=email)
#             # In production, send actual email
#             messages.success(request, 'Password reset link has been sent to your email')
#         except User.DoesNotExist:
#             messages.error(request, 'No account found with this email')
#         return redirect('login')
    
#     return render(request, 'shop/password_reset.html')