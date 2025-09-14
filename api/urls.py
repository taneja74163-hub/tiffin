from django.urls import path
from .views import signup, hello, add_customer, mark_tiffin, customer_detail, customer_stats, edit_customer, delete_customer, customer_meal_history, home, update_specific_date, get_date_status

urlpatterns = [
    path("", home, name="home"),  # Home endpoint
    path("signup/", signup, name="signup"),
    path("hello/", hello, name="hello"),  # test endpoint
    path("add_customer/", add_customer, name="add_customer"),
    path("mark_tiffin/", mark_tiffin, name="mark_tiffin"),
    path("customer/<str:id>/", customer_detail, name="customer_detail"),
    path("customer/<str:id>/stats/", customer_stats, name="customer_stats"),
    path("customer/<str:id>/edit/", edit_customer, name="edit_customer"),
    path("customer/<str:customer_id>/delete/", delete_customer, name="delete_customer"),
    path("customer/<str:customer_id>/meal-history/", customer_meal_history, name="customer_meal_history"),
    path("update_specific_date/", update_specific_date, name="update_specific_date"),
    path("customer/<str:customer_id>/date-status/", get_date_status, name="get_date_status"),
]
