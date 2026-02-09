from django.urls import path
from . import views

urlpatterns = [
    path('process/<int:order_id>/', views.payment, name='payment_process'),
    path('callback/', views.payment_callback, name='payment_callback'),
]
