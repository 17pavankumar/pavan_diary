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
from orders.models import Order, OrderItem, Payment

# Razorpay imports - wrapped in try-except for development without razorpay
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
    # Initialize Razorpay client only if keys are available
    if hasattr(settings, 'RAZORPAY_KEY_ID') and hasattr(settings, 'RAZORPAY_KEY_SECRET'):
        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    else:
        razorpay_client = None
        RAZORPAY_AVAILABLE = False
except ImportError:
    RAZORPAY_AVAILABLE = False
    razorpay_client = None


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
    return render(request, 'orders/checkout.html', context)


@login_required
def payment(request, order_id):
    """Payment processing page with Razorpay integration"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # If already paid, redirect to order detail
    if order.payment_status == 'completed':
        messages.info(request, 'This order has already been paid')
        return redirect('order_detail', order_id=order.id)
    
    # Check if Razorpay is available
    if not RAZORPAY_AVAILABLE or not razorpay_client:
        messages.error(request, 'Online payment is currently unavailable. Please use Cash on Delivery.')
        return redirect('order_detail', order_id=order.id)
    
    # Create Razorpay order if not already created
    if not order.razorpay_order_id:
        try:
            razorpay_order = razorpay_client.order.create({
                'amount': order.get_amount_in_paise(),
                'currency': 'INR',
                'payment_capture': '1',
                'notes': {
                    'order_number': order.order_number,
                    'customer_name': order.customer.get_full_name() or order.customer.username
                }
            })
            order.razorpay_order_id = razorpay_order['id']
            order.save()
        except Exception as e:
            messages.error(request, f'Unable to create payment: {str(e)}')
            return redirect('order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': order.razorpay_order_id,
        'amount': order.get_amount_in_paise(),
        'currency': 'INR',
        'customer_name': order.customer.get_full_name() or order.customer.username,
        'customer_email': order.customer.email,
        'customer_phone': order.phone,
    }
    return render(request, 'orders/payment.html', context)


@csrf_exempt
def payment_callback(request):
    """Handle Razorpay payment callback"""
    if request.method == 'POST':
        try:
            # Check if Razorpay is available
            if not RAZORPAY_AVAILABLE or not razorpay_client:
                messages.error(request, 'Payment processing unavailable.')
                return redirect('home')
            
            # Get payment details from request
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            
            # Get the order
            order = get_object_or_404(Order, razorpay_order_id=razorpay_order_id)
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify signature
            try:
                razorpay_client.utility.verify_payment_signature(params_dict)
                
                # Payment successful
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_signature = razorpay_signature
                order.payment_status = 'completed'
                order.status = 'confirmed'
                order.save()
                
                # Create payment record
                Payment.objects.create(
                    order=order,
                    transaction_id=razorpay_payment_id,
                    amount=order.total_amount,
                    payment_method='Razorpay',
                    status='completed',
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_signature=razorpay_signature,
                    payment_date=datetime.now()
                )
                
                messages.success(request, '✅ Payment successful! Your order has been confirmed.')
                return redirect('order_detail', order_id=order.id)
                
            except Exception as e:
                # Payment signature verification failed
                order.payment_status = 'failed'
                order.save()
                messages.error(request, f'❌ Payment verification failed: {str(e)}')
                return redirect('order_detail', order_id=order.id)
                
        except Exception as e:
            messages.error(request, f'❌ Payment processing error: {str(e)}')
            return redirect('home')
    
    return redirect('home')


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
