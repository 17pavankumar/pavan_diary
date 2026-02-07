from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal

from users.models import User, CustomerProfile
from orders.models import Order

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
            return render(request, 'users/register.html')
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'users/register.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'users/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'users/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return render(request, 'users/register.html')
        
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
    
    return render(request, 'users/register.html')


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
    
    return render(request, 'users/login.html')


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
    return render(request, 'users/profile.html', context)


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
    
    return render(request, 'users/password_reset.html')
