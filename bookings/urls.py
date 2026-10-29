from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_bookings, name='my_bookings'),
    path('book/<str:plan_type>/', views.book_view, name='book'),
    path('payment/<int:pk>/', views.payment_view, name='payment'),
    path('payment/<int:pk>/confirm/', views.payment_confirm, name='payment_confirm'),
    path('cancel/<int:pk>/', views.cancel_slot, name='cancel_slot'),
    path('success/', views.booking_success, name='booking_success'),
]