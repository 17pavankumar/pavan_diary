from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal

from products.models import Product
from cart.models import CartItem, Wishlist

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
    return render(request, 'cart/cart.html', context)


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
    return render(request, 'cart/wishlist.html', context)


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
