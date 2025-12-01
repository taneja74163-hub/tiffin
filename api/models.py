# models.py
from django.db import models
from django.contrib.auth.models import User
from datetime import date

class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=100)
    joining_date = models.DateField(default=date.today)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Cached statistics
    current_month = models.CharField(max_length=7, default='0000-00')
    lunches_this_month = models.IntegerField(default=0)
    dinners_this_month = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'name']),
            models.Index(fields=['joining_date']),
        ]
    
    def __str__(self):
        return self.name

class DailyMeal(models.Model):
    MEAL_CHOICES = [
        ('L', 'Lunch'),
        ('D', 'Dinner'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='meals')
    date = models.DateField()
    meal_type = models.CharField(max_length=1, choices=MEAL_CHOICES)
    is_taken = models.BooleanField(default=True)

    class Meta:
        unique_together = ['customer', 'date', 'meal_type']
        ordering = ['-date', 'meal_type']

    MEAL_CHOICES = [
        ('L', 'Lunch'),
        ('D', 'Dinner'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='meals')
    date = models.DateField()
    meal_type = models.CharField(max_length=1, choices=MEAL_CHOICES)
    is_taken = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['customer', 'date', 'meal_type']
        indexes = [
            models.Index(fields=['customer', 'date']),
            models.Index(fields=['date']),
        ]
        ordering = ['-date', 'meal_type']
    
    def __str__(self):
        return f"{self.customer.name} - {self.date} - {self.meal_type}"