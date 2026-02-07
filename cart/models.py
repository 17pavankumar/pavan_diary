from django.db import models
from django.core.validators import MinValueValidator
from users.models import User
from products.models import Product

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
