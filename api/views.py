from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import date
import json

from .models import Customer, TiffinStatus
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import calendar
from django.views.decorators.http import require_GET


# ----------------------------
# Customer APIs
# ----------------------------

@require_GET
def home(request):
    return JsonResponse({
        "message": "Welcome to the Tiffin Service API!",
        "status": "OK"
    })


# Signup API
@csrf_exempt
def signup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")

            if not username or not password:
                return JsonResponse({"error": "Username and password required"}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({"error": "Username already exists"}, status=400)

            user = User.objects.create_user(username=username, email=email, password=password)
            return JsonResponse({"message": "User created successfully"}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def add_customer(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer = Customer.objects.create(
                name=data.get('name'),
                joining_date=data.get('joining_date'),
                fee=data.get('fee')
            )
            # Automatically create today's TiffinStatus
            TiffinStatus.objects.get_or_create(customer=customer, date=date.today())
            return JsonResponse({'success': True, 'id': customer.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


@csrf_exempt
def edit_customer(request, id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            c = Customer.objects.get(id=id)
            c.name = data.get('name', c.name)
            c.joining_date = data.get('joining_date', c.joining_date)
            c.fee = data.get('fee', c.fee)
            c.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


@api_view(['DELETE'])
def delete_customer(request, customer_id):
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        customer.delete()
        return Response({"success": True, "message": "Customer deleted successfully"})
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def mark_tiffin(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_id = data.get('customer_id')
            slot = data.get('slot')  # 'lunch' or 'dinner'
            value = data.get('value')  # true/false
            today = date.today()
            status, _ = TiffinStatus.objects.get_or_create(customer_id=customer_id, date=today)
            if slot == 'lunch':
                status.lunch = value
            elif slot == 'dinner':
                status.dinner = value
            status.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


# ----------------------------
# Customer Details & Stats
# ----------------------------

@csrf_exempt
def hello(request):
    today = date.today()
    customers = Customer.objects.all()
    result = []
    for c in customers:
        status, _ = TiffinStatus.objects.get_or_create(customer=c, date=today)
        result.append({
            'id': c.id,
            'name': c.name,
            'lunch': status.lunch,
            'dinner': status.dinner
        })
    return JsonResponse({"customers": result})


@csrf_exempt
def customer_detail(request, id):
    try:
        c = Customer.objects.get(id=id)
        data = {
            'id': c.id,
            'name': c.name,
            'joining_date': str(c.joining_date),
            'fee': str(c.fee),
        }
        return JsonResponse(data)
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)


@csrf_exempt
def customer_stats(request, id):
    today = date.today()
    month_start = today.replace(day=1)
    lunches = TiffinStatus.objects.filter(customer_id=id, date__gte=month_start, date__lte=today, lunch=True).count()
    dinners = TiffinStatus.objects.filter(customer_id=id, date__gte=month_start, date__lte=today, dinner=True).count()
    return JsonResponse({"lunches": lunches, "dinners": dinners})

@api_view(['GET'])
def customer_meal_history(request, customer_id):
    try:
        customer = get_object_or_404(Customer, id=customer_id)

        # Get date range: from joining_date to today
        today = datetime.now().date()
        start_date = customer.joining_date
        num_days = (today - start_date).days + 1  # include today

        daily_meals = []

        for i in range(num_days):
            date = start_date + timedelta(days=i)
            is_weekend = date.weekday() >= 5  # Saturday=5, Sunday=6

            # Get meal record for this date
            meal_record = TiffinStatus.objects.filter(customer=customer, date=date).first()

            daily_meals.append({
                'date': date.isoformat(),
                'lunch': meal_record.lunch if meal_record else False,
                'dinner': meal_record.dinner if meal_record else False,
                'is_weekend': is_weekend
            })

        # Calculate statistics
        total_lunches = sum(1 for day in daily_meals if day['lunch'] and not day['is_weekend'])
        total_dinners = sum(1 for day in daily_meals if day['dinner'] and not day['is_weekend'])
        total_possible_meals = sum(1 for day in daily_meals if not day['is_weekend']) * 2

        return Response({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'joining_date': customer.joining_date,
                'fee': customer.fee
            },
            'daily_meals': daily_meals,
            'statistics': {
                'lunches_taken': total_lunches,
                'dinners_taken': total_dinners,
                'total_meals_taken': total_lunches + total_dinners,
                'total_possible_meals': total_possible_meals,
                'completion_rate': round(((total_lunches + total_dinners) / total_possible_meals * 100), 2) if total_possible_meals > 0 else 0
            }
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Get start of current month
        today = datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get all TiffinStatus records for this customer in the current month
        tiffin_records = TiffinStatus.objects.filter(
            customer=customer,
            date__gte=start_of_month.date(),
            date__lte=today.date()
        )
        
        # Create a dictionary for quick lookup
        tiffin_dict = {record.date: record for record in tiffin_records}
        
        # Get all dates in current month up to today
        num_days = calendar.monthrange(today.year, today.month)[1]
        dates_in_month = [start_of_month + timedelta(days=i) for i in range(num_days)]
        dates_up_to_today = [date for date in dates_in_month if date.date() <= today.date()]
        
        daily_meals = []
        
        for date in dates_up_to_today:
            # Check if it's a weekend
            is_weekend = date.weekday() >= 5  # 5 = Saturday, 6 = Sunday
            
            # Get TiffinStatus record for this date
            tiffin_status = tiffin_dict.get(date.date())
            
            if tiffin_status:
                lunch_taken = tiffin_status.lunch
                dinner_taken = tiffin_status.dinner
            else:
                # Default values from your model
                lunch_taken = True
                dinner_taken = True
            
            daily_meals.append({
                'date': date.date().isoformat(),
                'lunch': lunch_taken,
                'dinner': dinner_taken,
                'is_weekend': is_weekend
            })
        
        # Calculate statistics
        total_lunches = sum(1 for day in daily_meals if day['lunch'] and not day['is_weekend'])
        total_dinners = sum(1 for day in daily_meals if day['dinner'] and not day['is_weekend'])
        total_possible_meals = sum(1 for day in daily_meals if not day['is_weekend']) * 2
        
        return Response({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'joining_date': customer.joining_date,
                'fee': customer.fee
            },
            'daily_meals': daily_meals,
            'statistics': {
                'lunches_taken': total_lunches,
                'dinners_taken': total_dinners,
                'total_meals_taken': total_lunches + total_dinners,
                'total_possible_meals': total_possible_meals,
                'completion_rate': round(((total_lunches + total_dinners) / total_possible_meals * 100), 2) if total_possible_meals > 0 else 0
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)