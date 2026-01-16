from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class User(AbstractUser):
    """Extended User model for authentication"""
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix for groups and user_permissions clash
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='shop_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='shop_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username


class CustomerProfile(models.Model):
    """Customer profile with additional information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_profiles'

    def __str__(self):
        return f"{self.user.username}'s Profile"


class SellerProfile(models.Model):
    """Seller profile for dairy product vendors"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=200)
    business_license = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, 
                                validators=[MinValueValidator(0), MaxValueValidator(5)])
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seller_profiles'

    def __str__(self):
        return self.business_name


class Category(models.Model):
    """Product categories (Milk, Cheese, Yogurt, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Dairy products"""
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=50, default='piece')  # piece, liter, kg, etc.
    is_organic = models.BooleanField(default=False)
    expiry_days = models.IntegerField(help_text="Days until expiry from production")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00,
                                validators=[MinValueValidator(0), MaxValueValidator(5)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0
    
    @property
    def primary_image(self):
        """Get the primary product image or first image"""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image.url
        first_image = self.images.first()
        if first_image:
            return first_image.image.url
        return None


class ProductImage(models.Model):
    """Multiple images for products"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'

    def __str__(self):
        return f"Image for {self.product.name}"


class Order(models.Model):
    """Customer orders"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    shipping_address = models.TextField()
    phone = models.CharField(max_length=15)
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=20, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number}"


class OrderItem(models.Model):
    """Items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity}x {self.product.name if self.product else 'Deleted Product'}"

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price
        super().save(*args, **kwargs)


class CartItem(models.Model):
    """Shopping cart items"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username}'s cart: {self.product.name}"

    @property
    def subtotal(self):
        return self.quantity * self.product.price


class Payment(models.Model):
    """Payment transactions"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"


class Review(models.Model):
    """Product reviews"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s review of {self.product.name}"


class Wishlist(models.Model):
    """User wishlist for favorite products"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlist'
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username}'s wishlist: {self.product.name}"


class ProductListing(models.Model):
    """Product listing management"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='listing')
    featured = models.BooleanField(default=False)
    on_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_listings'

    def __str__(self):
        return f"Listing for {self.product.name}"

    @property
    def effective_price(self):
        if self.on_sale and self.sale_price:
            return self.sale_price
        return self.product.price




# from django.db import models
# from django.contrib.auth.models import AbstractUser
# from django.core.validators import MinValueValidator, MaxValueValidator
# from decimal import Decimal

# class User(AbstractUser):
#     """Extended User model for authentication"""
#     phone = models.CharField(max_length=15, blank=True)
#     address = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     # Fix for groups and user_permissions clash
#     groups = models.ManyToManyField(
#         'auth.Group',
#         related_name='shop_user_set',
#         blank=True,
#         help_text='The groups this user belongs to.',
#         verbose_name='groups',
#     )
#     user_permissions = models.ManyToManyField(
#         'auth.Permission',
#         related_name='shop_user_set',
#         blank=True,
#         help_text='Specific permissions for this user.',
#         verbose_name='user permissions',
#     )

#     class Meta:
#         db_table = 'users'

#     def __str__(self):
#         return self.username


# class CustomerProfile(models.Model):
#     """Customer profile with additional information"""
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
#     date_of_birth = models.DateField(null=True, blank=True)
#     profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
#     loyalty_points = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'customer_profiles'

#     def __str__(self):
#         return f"{self.user.username}'s Profile"


# class SellerProfile(models.Model):
#     """Seller profile for dairy product vendors"""
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
#     business_name = models.CharField(max_length=200)
#     business_license = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, 
#                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
#     is_verified = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'seller_profiles'

#     def __str__(self):
#         return self.business_name


# class Category(models.Model):
#     """Product categories (Milk, Cheese, Yogurt, etc.)"""
#     name = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)
#     image = models.ImageField(upload_to='categories/', null=True, blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'categories'
#         verbose_name_plural = 'Categories'

#     def __str__(self):
#         return self.name


# class Product(models.Model):
#     """Dairy products"""
#     seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
#     category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
#     name = models.CharField(max_length=200)
#     description = models.TextField()
#     price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
#     unit = models.CharField(max_length=50, default='piece')  # piece, liter, kg, etc.
#     is_organic = models.BooleanField(default=False)
#     expiry_days = models.IntegerField(help_text="Days until expiry from production")
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00,
#                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'products'
#         ordering = ['-created_at']

#     def __str__(self):
#         return self.name

#     @property
#     def is_in_stock(self):
#         return self.stock_quantity > 0


# class ProductImage(models.Model):
#     """Multiple images for products"""
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
#     image = models.ImageField(upload_to='products/')
#     is_primary = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'product_images'

#     def __str__(self):
#         return f"Image for {self.product.name}"


# class Order(models.Model):
#     """Customer orders"""
#     STATUS_CHOICES = [
#         ('pending', 'Pending'),
#         ('confirmed', 'Confirmed'),
#         ('processing', 'Processing'),
#         ('shipped', 'Shipped'),
#         ('delivered', 'Delivered'),
#         ('cancelled', 'Cancelled'),
#     ]

#     customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
#     order_number = models.CharField(max_length=50, unique=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     shipping_address = models.TextField()
#     phone = models.CharField(max_length=15)
#     payment_method = models.CharField(max_length=50)
#     payment_status = models.CharField(max_length=20, default='pending')
#     notes = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'orders'
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"Order {self.order_number}"


# class OrderItem(models.Model):
#     """Items in an order"""
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
#     product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
#     quantity = models.IntegerField(validators=[MinValueValidator(1)])
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     subtotal = models.DecimalField(max_digits=10, decimal_places=2)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'order_items'

#     def __str__(self):
#         return f"{self.quantity}x {self.product.name if self.product else 'Deleted Product'}"

#     def save(self, *args, **kwargs):
#         self.subtotal = self.quantity * self.price
#         super().save(*args, **kwargs)


# class CartItem(models.Model):
#     """Shopping cart items"""
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'cart_items'
#         unique_together = ['user', 'product']

#     def __str__(self):
#         return f"{self.user.username}'s cart: {self.product.name}"

#     @property
#     def subtotal(self):
#         return self.quantity * self.product.price


# class Payment(models.Model):
#     """Payment transactions"""
#     PAYMENT_STATUS = [
#         ('pending', 'Pending'),
#         ('completed', 'Completed'),
#         ('failed', 'Failed'),
#         ('refunded', 'Refunded'),
#     ]

#     order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
#     transaction_id = models.CharField(max_length=100, unique=True)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_method = models.CharField(max_length=50)
#     status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
#     payment_date = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'payments'

#     def __str__(self):
#         return f"Payment {self.transaction_id} - {self.status}"


# class Review(models.Model):
#     """Product reviews"""
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
#     comment = models.TextField()
#     is_verified_purchase = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'reviews'
#         unique_together = ['product', 'user']

#     def __str__(self):
#         return f"{self.user.username}'s review of {self.product.name}"


# class Wishlist(models.Model):
#     """User wishlist for favorite products"""
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'wishlist'
#         unique_together = ['user', 'product']

#     def __str__(self):
#         return f"{self.user.username}'s wishlist: {self.product.name}"


# class ProductListing(models.Model):
#     """Product listing management"""
#     product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='listing')
#     featured = models.BooleanField(default=False)
#     on_sale = models.BooleanField(default=False)
#     sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     view_count = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'product_listings'

#     def __str__(self):
#         return f"Listing for {self.product.name}"

#     @property
#     def effective_price(self):
#         if self.on_sale and self.sale_price:
#             return self.sale_price
#         return self.product.price





# from django.db import models

# # Create your models here.
# from django.contrib.auth.models import AbstractUser
# from django.core.validators import MinValueValidator, MaxValueValidator
# from decimal import Decimal

# class User(AbstractUser):
#     """Extended User model for authentication"""
#     phone = models.CharField(max_length=15, blank=True)
#     address = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'users'

#     def __str__(self):
#         return self.username


# class CustomerProfile(models.Model):
#     """Customer profile with additional information"""
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
#     date_of_birth = models.DateField(null=True, blank=True)
#     profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
#     loyalty_points = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'customer_profiles'

#     def __str__(self):
#         return f"{self.user.username}'s Profile"


# class SellerProfile(models.Model):
#     """Seller profile for dairy product vendors"""
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
#     business_name = models.CharField(max_length=200)
#     business_license = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, 
#                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
#     is_verified = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'seller_profiles'

#     def __str__(self):
#         return self.business_name


# class Category(models.Model):
#     """Product categories (Milk, Cheese, Yogurt, etc.)"""
#     name = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)
#     image = models.ImageField(upload_to='categories/', null=True, blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'categories'
#         verbose_name_plural = 'Categories'

#     def __str__(self):
#         return self.name


# class Product(models.Model):
#     """Dairy products"""
#     seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
#     category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
#     name = models.CharField(max_length=200)
#     description = models.TextField()
#     price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
#     unit = models.CharField(max_length=50, default='piece')  # piece, liter, kg, etc.
#     is_organic = models.BooleanField(default=False)
#     expiry_days = models.IntegerField(help_text="Days until expiry from production")
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00,
#                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'products'
#         ordering = ['-created_at']

#     def __str__(self):
#         return self.name

#     @property
#     def is_in_stock(self):
#         return self.stock_quantity > 0


# class ProductImage(models.Model):
#     """Multiple images for products"""
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
#     image = models.ImageField(upload_to='products/')
#     is_primary = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'product_images'

#     def __str__(self):
#         return f"Image for {self.product.name}"


# class Order(models.Model):
#     """Customer orders"""
#     STATUS_CHOICES = [
#         ('pending', 'Pending'),
#         ('confirmed', 'Confirmed'),
#         ('processing', 'Processing'),
#         ('shipped', 'Shipped'),
#         ('delivered', 'Delivered'),
#         ('cancelled', 'Cancelled'),
#     ]

#     customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
#     order_number = models.CharField(max_length=50, unique=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     shipping_address = models.TextField()
#     phone = models.CharField(max_length=15)
#     payment_method = models.CharField(max_length=50)
#     payment_status = models.CharField(max_length=20, default='pending')
#     notes = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'orders'
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"Order {self.order_number}"


# class OrderItem(models.Model):
#     """Items in an order"""
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
#     product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
#     quantity = models.IntegerField(validators=[MinValueValidator(1)])
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     subtotal = models.DecimalField(max_digits=10, decimal_places=2)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'order_items'

#     def __str__(self):
#         return f"{self.quantity}x {self.product.name if self.product else 'Deleted Product'}"

#     def save(self, *args, **kwargs):
#         self.subtotal = self.quantity * self.price
#         super().save(*args, **kwargs)


# class CartItem(models.Model):
#     """Shopping cart items"""
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'cart_items'
#         unique_together = ['user', 'product']

#     def __str__(self):
#         return f"{self.user.username}'s cart: {self.product.name}"

#     @property
#     def subtotal(self):
#         return self.quantity * self.product.price


# class Payment(models.Model):
#     """Payment transactions"""
#     PAYMENT_STATUS = [
#         ('pending', 'Pending'),
#         ('completed', 'Completed'),
#         ('failed', 'Failed'),
#         ('refunded', 'Refunded'),
#     ]

#     order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
#     transaction_id = models.CharField(max_length=100, unique=True)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_method = models.CharField(max_length=50)
#     status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
#     payment_date = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'payments'

#     def __str__(self):
#         return f"Payment {self.transaction_id} - {self.status}"


# class Review(models.Model):
#     """Product reviews"""
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
#     comment = models.TextField()
#     is_verified_purchase = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'reviews'
#         unique_together = ['product', 'user']

#     def __str__(self):
#         return f"{self.user.username}'s review of {self.product.name}"


# class ProductListing(models.Model):
#     """Product listing management"""
#     product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='listing')
#     featured = models.BooleanField(default=False)
#     on_sale = models.BooleanField(default=False)
#     sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     view_count = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'product_listings'

#     def __str__(self):
#         return f"Listing for {self.product.name}"

#     @property
#     def effective_price(self):
#         if self.on_sale and self.sale_price:
#             return self.sale_price
#         return self.product.price


# from django.db import models
# from django.contrib.auth.models import AbstractUser
# from django.core.validators import MinValueValidator, MaxValueValidator
# from decimal import Decimal

# class User(AbstractUser):
#     """Extended User model for authentication"""
#     phone = models.CharField(max_length=15, blank=True)
#     address = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     # Fix for groups and user_permissions clash
#     groups = models.ManyToManyField(
#         'auth.Group',
#         related_name='shop_user_set',
#         blank=True,
#         help_text='The groups this user belongs to.',
#         verbose_name='groups',
#     )
#     user_permissions = models.ManyToManyField(
#         'auth.Permission',
#         related_name='shop_user_set',
#         blank=True,
#         help_text='Specific permissions for this user.',
#         verbose_name='user permissions',
#     )

#     class Meta:
#         db_table = 'users'

#     def __str__(self):
#         return self.username


# class CustomerProfile(models.Model):
#     """Customer profile with additional information"""
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
#     date_of_birth = models.DateField(null=True, blank=True)
#     profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
#     loyalty_points = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'customer_profiles'

#     def __str__(self):
#         return f"{self.user.username}'s Profile"


# class SellerProfile(models.Model):
#     """Seller profile for dairy product vendors"""
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
#     business_name = models.CharField(max_length=200)
#     business_license = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, 
#                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
#     is_verified = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'seller_profiles'

#     def __str__(self):
#         return self.business_name


# class Category(models.Model):
#     """Product categories (Milk, Cheese, Yogurt, etc.)"""
#     name = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)
#     image = models.ImageField(upload_to='categories/', null=True, blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'categories'
#         verbose_name_plural = 'Categories'

#     def __str__(self):
#         return self.name


# class Product(models.Model):
#     """Dairy products"""
#     seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
#     category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
#     name = models.CharField(max_length=200)
#     description = models.TextField()
#     price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
#     unit = models.CharField(max_length=50, default='piece')  # piece, liter, kg, etc.
#     is_organic = models.BooleanField(default=False)
#     expiry_days = models.IntegerField(help_text="Days until expiry from production")
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00,
#                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'products'
#         ordering = ['-created_at']

#     def __str__(self):
#         return self.name

#     @property
#     def is_in_stock(self):
#         return self.stock_quantity > 0


# class ProductImage(models.Model):
#     """Multiple images for products"""
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
#     image = models.ImageField(upload_to='products/')
#     is_primary = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'product_images'

#     def __str__(self):
#         return f"Image for {self.product.name}"


# class Order(models.Model):
#     """Customer orders"""
#     STATUS_CHOICES = [
#         ('pending', 'Pending'),
#         ('confirmed', 'Confirmed'),
#         ('processing', 'Processing'),
#         ('shipped', 'Shipped'),
#         ('delivered', 'Delivered'),
#         ('cancelled', 'Cancelled'),
#     ]

#     customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
#     order_number = models.CharField(max_length=50, unique=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     shipping_address = models.TextField()
#     phone = models.CharField(max_length=15)
#     payment_method = models.CharField(max_length=50)
#     payment_status = models.CharField(max_length=20, default='pending')
#     notes = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'orders'
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"Order {self.order_number}"


# class OrderItem(models.Model):
#     """Items in an order"""
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
#     product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
#     quantity = models.IntegerField(validators=[MinValueValidator(1)])
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     subtotal = models.DecimalField(max_digits=10, decimal_places=2)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'order_items'

#     def __str__(self):
#         return f"{self.quantity}x {self.product.name if self.product else 'Deleted Product'}"

#     def save(self, *args, **kwargs):
#         self.subtotal = self.quantity * self.price
#         super().save(*args, **kwargs)


# class CartItem(models.Model):
#     """Shopping cart items"""
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'cart_items'
#         unique_together = ['user', 'product']

#     def __str__(self):
#         return f"{self.user.username}'s cart: {self.product.name}"

#     @property
#     def subtotal(self):
#         return self.quantity * self.product.price


# class Payment(models.Model):
#     """Payment transactions"""
#     PAYMENT_STATUS = [
#         ('pending', 'Pending'),
#         ('completed', 'Completed'),
#         ('failed', 'Failed'),
#         ('refunded', 'Refunded'),
#     ]

#     order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
#     transaction_id = models.CharField(max_length=100, unique=True)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_method = models.CharField(max_length=50)
#     status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
#     payment_date = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'payments'

#     def __str__(self):
#         return f"Payment {self.transaction_id} - {self.status}"


# class Review(models.Model):
#     """Product reviews"""
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
#     comment = models.TextField()
#     is_verified_purchase = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'reviews'
#         unique_together = ['product', 'user']

#     def __str__(self):
#         return f"{self.user.username}'s review of {self.product.name}"


# class Wishlist(models.Model):
#     """User wishlist for favorite products"""
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'wishlist'
#         unique_together = ['user', 'product']

#     def __str__(self):
#         return f"{self.user.username}'s wishlist: {self.product.name}"


# class ProductListing(models.Model):
#     """Product listing management"""
#     product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='listing')
#     featured = models.BooleanField(default=False)
#     on_sale = models.BooleanField(default=False)
#     sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     view_count = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'product_listings'

#     def __str__(self):
#         return f"Listing for {self.product.name}"

#     @property
#     def effective_price(self):
#         if self.on_sale and self.sale_price:
#             return self.sale_price
#         return self.product.price