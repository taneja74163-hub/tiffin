from django.urls import path
from . import views

urlpatterns = [
    # Home & Authentication
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    
    # Customer CRUD
    path('add_customer/', views.add_customer, name='add_customer'),
    path('hello/', views.hello, name='hello'),
    path('customer/<int:id>/', views.customer_detail, name='customer_detail'),
    path('edit_customer/<int:id>/', views.edit_customer, name='edit_customer'),
    path('delete_customer/<int:customer_id>/', views.delete_customer, name='delete_customer'),
    
    # Meal Management
    path('mark_tiffin/', views.mark_tiffin, name='mark_tiffin'),
    path('update_specific_date/', views.update_specific_date, name='update_specific_date'),
    
    # Stats & Reports
    path('customer/<int:id>/stats/', views.customer_stats, name='customer_stats'),
    path('customer/<int:customer_id>/meal-history/', views.customer_meal_history, name='customer_meal_history'),
    path('customer/<int:customer_id>/date-status/', views.get_date_status, name='get_date_status'),
    # path('customer/<int:customer_id>/pdf/', views.generate_customer_pdf, name='generate_customer_pdf'),
    path('customer/<int:customer_id>/download-pdf/', views.download_customer_pdf, name='download_customer_pdf'),
]