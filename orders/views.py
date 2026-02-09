from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from decimal import Decimal
import uuid
from datetime import datetime

from products.models import Product
from cart.models import CartItem
from orders.models import Order, OrderItem




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
        # Get form data
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        notes = request.POST.get('notes', '').strip()
        save_address = request.POST.get('save_address')
        payment_method = request.POST.get('payment_method', 'COD')
        
        # Validation
        if not all([full_name, phone, address, city, state, pincode]):
            messages.error(request, 'Please fill all required fields')
            return render(request, 'orders/checkout.html', {
                'cart_items': cart_items,
                'subtotal': subtotal,
                'shipping': shipping,
                'total': total,
            })
        
        # Validate phone number (basic validation)
        if not phone.isdigit() or len(phone) < 10:
            messages.error(request, 'Please enter a valid phone number')
            return render(request, 'orders/checkout.html', {
                'cart_items': cart_items,
                'subtotal': subtotal,
                'shipping': shipping,
                'total': total,
            })
            
        # Save address to profile if requested or if empty
        user = request.user
        if save_address or not user.address:
            user.phone = phone
            user.address = address
            user.city = city
            user.state = state
            user.pincode = pincode
            user.save()
        
        # Combine address for order record
        full_address = f"{address}, {city}, {state} - {pincode}"
        
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
        
        if payment_method == 'COD':
            # For COD, mark as pending and go to order detail
            order.status = 'confirmed'
            order.save()
            messages.success(request, f'✅ Order {order.order_number} placed successfully!')
            return redirect('order_detail', order_id=order.id)
        else:
            # For online payment, redirect to payment page
            return redirect('payment_process', order_id=order.id)
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'orders/checkout.html', context)





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
    return render(request, 'orders/order_list.html', context)


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
    return render(request, 'orders/order_detail.html', context)


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
