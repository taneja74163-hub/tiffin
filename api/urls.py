from django.urls import path
from .views import signup, hello, add_customer, mark_tiffin, customer_detail, customer_stats, edit_customer, delete_customer, customer_meal_history

urlpatterns = [
    path("", home, name="home"),  # Home endpoint
    path("signup/", signup, name="signup"),
    path("hello/", hello, name="hello"),  # test endpoint
    path("add_customer/", add_customer, name="add_customer"),
    path("mark_tiffin/", mark_tiffin, name="mark_tiffin"),
    path("customer/<int:id>/", customer_detail, name="customer_detail"),
    path("customer/<int:id>/stats/", customer_stats, name="customer_stats"),
    path("customer/<int:id>/edit/", edit_customer, name="edit_customer"),
    path('customer/<int:customer_id>/delete/', delete_customer, name='delete_customer'),
    path('customer/<int:customer_id>/meal-history/', customer_meal_history, name='customer_meal_history'),
]
