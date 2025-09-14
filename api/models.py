# api/models.py
from django.db import models
from datetime import date
from djongo.models import ObjectIdField

class Customer(models.Model):
    _id = ObjectIdField(primary_key=True, editable=False)
    name = models.CharField(max_length=100)
    joining_date = models.DateField(default=date.today)
    fee = models.FloatField()  # Changed from DecimalField to FloatField
    tiffin_status = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customer_collection'

    def __str__(self):
        return self.name

    def get_status_for_date(self, target_date):
        """Get lunch/dinner status for a specific date"""
        date_str = target_date.isoformat()
        if not self.tiffin_status:
            self.tiffin_status = {}
        return self.tiffin_status.get(date_str, {'lunch': True, 'dinner': True})

    def set_status_for_date(self, target_date, lunch=False, dinner=False):
        """Set lunch/dinner status for a specific date"""
        date_str = target_date.isoformat()
        if not self.tiffin_status:
            self.tiffin_status = {}
            
        if date_str not in self.tiffin_status:
            self.tiffin_status[date_str] = {'lunch': lunch, 'dinner': dinner}
        else:
            if lunch is not None:
                self.tiffin_status[date_str]['lunch'] = lunch
            if dinner is not None:
                self.tiffin_status[date_str]['dinner'] = dinner

    def save(self, *args, **kwargs):
        if self.tiffin_status is None:
            self.tiffin_status = {}
        super().save(*args, **kwargs)