from django.db import models

class Customer(models.Model):
	name = models.CharField(max_length=100)
	joining_date = models.DateField()
	fee = models.DecimalField(max_digits=8, decimal_places=2)

	def __str__(self):
		return self.name

# Create your models here.

class TiffinStatus(models.Model):
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
	date = models.DateField()
	lunch = models.BooleanField(default=True)
	dinner = models.BooleanField(default=True)

	class Meta:
		unique_together = ('customer', 'date')
