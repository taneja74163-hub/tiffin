from django.contrib import admin
from .models import Customer, DailyMeal


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "user",
        "joining_date",
        "fee",
        "current_month",
        "lunches_this_month",
        "dinners_this_month",
    )
    list_filter = ("joining_date", "user")
    search_fields = ("name", "user__username")
    ordering = ("name",)


@admin.register(DailyMeal)
class DailyMealAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "date",
        "meal_type",
        "is_taken_display",
        "created_display",
    )

    list_filter = (
        "meal_type",
        "is_taken",
        "date",
        "customer",
    )

    search_fields = (
        "customer__name",
        "customer__user__username",
    )

    ordering = ("-date",)

    # --- Custom fields for readability ---

    def is_taken_display(self, obj):
        return "✓ Taken" if obj.is_taken else "✗ Missed"
    is_taken_display.short_description = "Meal Status"

    def created_display(self, obj):
        return obj.date.strftime("%d %b %Y")
    created_display.short_description = "Day"
