from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime
from orders.models import Order
from cart.models import CartItem
from .models import Payment

# Razorpay imports
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    RAZORPAY_AVAILABLE = False

def get_razorpay_client():
    if not RAZORPAY_AVAILABLE:
        return None
    
    has_id = hasattr(settings, 'RAZORPAY_KEY_ID')
    has_secret = hasattr(settings, 'RAZORPAY_KEY_SECRET')
    
    if has_id and has_secret:
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    return None

@login_required
def payment(request, order_id):
    """Payment processing page with Razorpay integration"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # If already paid, redirect to order detail
    if order.payment_status == 'completed':
        messages.info(request, 'This order has already been paid')
        return redirect('order_detail', order_id=order.id)
    
    # Check if Razorpay is available
    client = get_razorpay_client()
    if not RAZORPAY_AVAILABLE or not client:
        # Restore stock and Cart Items
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
                
                CartItem.objects.create(
                    user=request.user,
                    product=item.product,
                    quantity=item.quantity
                )
        
        order.delete()
        messages.error(request, 'Online payment is currently unavailable. Please use Cash on Delivery.')
        return redirect('cart')
    
    # Verify if existing Razorpay order ID is valid
    if order.razorpay_order_id:
        try:
            client.order.fetch(order.razorpay_order_id)
        except Exception:
            # If invalid (e.g. key changed), clear it
            order.razorpay_order_id = None
            order.save()

    # Create new Razorpay order if needed
    if not order.razorpay_order_id:
        try:
            razorpay_order = client.order.create({
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
            # Restore stock and Cart Items if payment initiation fails
            for item in order.items.all():
                if item.product:
                    # Restore stock
                    item.product.stock_quantity += item.quantity
                    item.product.save()
                    
                    # Restore cart item
                    CartItem.objects.create(
                        user=request.user,
                        product=item.product,
                        quantity=item.quantity
                    )
            
            # Delete the order
            order.delete()
            
            error_message = str(e)
            if 'Authentication failed' in error_message:
                messages.error(request, 'Unable to initiate payment: Invalid API Keys. Please contact support.')
            else:
                messages.error(request, f'Unable to create payment: {error_message}')
            return redirect('cart')
    
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
    return render(request, 'payment/payment.html', context)


@csrf_exempt
def payment_callback(request):
    """Handle Razorpay payment callback"""
    if request.method == 'POST':
        try:
            # Check if Razorpay is available
            client = get_razorpay_client()
            if not RAZORPAY_AVAILABLE or not client:
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
                client.utility.verify_payment_signature(params_dict)
                
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
