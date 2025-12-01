from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("get-csrf/", views.get_csrf, name="get_csrf"),
    path("login/", views.login_view, name="login"),  # Added login endpoint
    path("hello/", views.hello, name="hello"),
    path("add_customer/", views.add_customer, name="add_customer"),
    path("mark_tiffin/", views.mark_tiffin, name="mark_tiffin"),
    path("customer/<int:id>/", views.customer_detail, name="customer_detail"),  # Changed to int
    path("customer/<int:id>/stats/", views.customer_stats, name="customer_stats"),  # Changed to int
    path("customer/<int:id>/edit/", views.edit_customer, name="edit_customer"),  # Changed to int
    path("customer/<int:customer_id>/delete/", views.delete_customer, name="delete_customer"),  # Changed to int
    path("customer/<int:customer_id>/meal-history/", views.customer_meal_history, name="customer_meal_history"),  # Changed to int
    path("update_specific_date/", views.update_specific_date, name="update_specific_date"),
    path("customer/<int:customer_id>/date-status/", views.get_date_status, name="get_date_status"),  # Changed to int
    path('api/customer/<int:customer_id>/pdf/', views.generate_customer_pdf, name='generate_customer_pdf')
]