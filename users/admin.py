from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CustomerProfile, SellerProfile

# Unregister the default User admin if needed, or just register the custom User model
# Since we are using a custom User model, we should register it.
# However, if we simply register UserAdmin, it might not pick up the custom fields easily without fieldsets modification.

class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Customer Profile'

class SellerProfileInline(admin.StackedInline):
    model = SellerProfile
    can_delete = False
    verbose_name_plural = 'Seller Profile'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [CustomerProfileInline, SellerProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'phone')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone', 'address')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone', 'address')}),
    )

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'business_license', 'is_verified', 'rating')
    list_filter = ('is_verified', 'rating')
    search_fields = ('business_name', 'user__username', 'business_license')

# CustomerProfile is handled inline, but we can register it separately too if needed.
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'loyalty_points')
    search_fields = ('user__username',)
