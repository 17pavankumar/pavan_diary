from .models import CartItem

def cart_count(request):
    if request.user.is_authenticated:
        from django.db.models import Sum
        result = CartItem.objects.filter(user=request.user).aggregate(total=Sum('quantity'))
        count = result['total'] or 0
    else:
        count = 0
    return {'cart_count': count}
