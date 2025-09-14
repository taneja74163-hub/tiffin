from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import date, datetime, timedelta
import json
import calendar
from bson import ObjectId

from .models import Customer
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET
from .utils import MongoDBJSONEncoder

# Helper function to convert ObjectId to string for JSON serialization
def serialize_customer(customer):
    return {
        'id': str(customer._id),
        'name': customer.name,
        'joining_date': customer.joining_date.isoformat(),
        'fee': float(customer.fee) if hasattr(customer.fee, 'to_decimal') else customer.fee,
        'tiffin_status': customer.tiffin_status
    }

# ----------------------------
# Customer APIs
# ----------------------------

@require_GET
def home(request):
    return JsonResponse({
        "message": "Welcome to the Tiffin Service API!",
        "status": "OK"
    })


# Signup API - Uses SQLite (default database)
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


# Customer operations - Use MongoDB
@csrf_exempt
def add_customer(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer = Customer.objects.create(
                name=data.get('name'),
                joining_date=data.get('joining_date'),
                fee=data.get('fee'),
                tiffin_status={}  # Initialize empty status dictionary
            )
            # Automatically create today's TiffinStatus
            today_str = date.today().isoformat()
            customer.set_status_for_date(date.today(), lunch=True, dinner=True)
            customer.save()
            return JsonResponse({'success': True, 'id': str(customer._id)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


@csrf_exempt
def edit_customer(request, id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Use the _id field for MongoDB
            customer = Customer.objects.get(_id=ObjectId(id))
            customer.name = data.get('name', customer.name)
            customer.joining_date = data.get('joining_date', customer.joining_date)
            customer.fee = data.get('fee', customer.fee)
            customer.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


@api_view(['DELETE'])
def delete_customer(request, customer_id):
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # Validate if the customer_id is a valid ObjectId
        try:
            obj_id = ObjectId(customer_id)
        except InvalidId:
            return Response({"success": False, "error": "Invalid customer ID format"}, status=400)
        
        # Delete the customer directly using the _id field
        result = Customer.objects.filter(_id=obj_id).delete()
        
        # Check if any document was deleted
        if result[0] > 0:
            return Response({"success": True, "message": "Customer deleted successfully"})
        else:
            return Response({"success": False, "error": "Customer not found"}, status=404)
            
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
            target_date_str = data.get('date', date.today().isoformat())
            
            # Parse date if provided as string
            if isinstance(target_date_str, str):
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            else:
                target_date = target_date_str
                
            # Use the _id field for MongoDB
            customer = Customer.objects.get(_id=ObjectId(customer_id))
            current_status = customer.get_status_for_date(target_date)
            
            if slot == 'lunch':
                customer.set_status_for_date(target_date, lunch=value, dinner=current_status['dinner'])
            elif slot == 'dinner':
                customer.set_status_for_date(target_date, lunch=current_status['lunch'], dinner=value)
                
            customer.save()
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
    for customer in customers:
        status = customer.get_status_for_date(today)
        result.append({
            'id': str(customer._id),  # Convert ObjectId to string
            'name': customer.name,
            'lunch': status['lunch'],
            'dinner': status['dinner']
        })
    return JsonResponse({"customers": result})


@csrf_exempt
def customer_detail(request, id):
    try:
        # Use the _id field for MongoDB
        customer = Customer.objects.get(_id=ObjectId(id))
        data = serialize_customer(customer)
        return JsonResponse(data)
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)


@csrf_exempt
def customer_stats(request, id):
    try:
        today = date.today()
        month_start = today.replace(day=1)
        # Use the _id field for MongoDB
        customer = Customer.objects.get(_id=ObjectId(id))
        
        # Count lunches and dinners for the month
        lunches = 0
        dinners = 0
        
        # Iterate through days in month
        current_date = month_start
        while current_date <= today:
            status = customer.get_status_for_date(current_date)
            if status['lunch']:
                lunches += 1
            if status['dinner']:
                dinners += 1
            current_date += timedelta(days=1)
            
        return JsonResponse({"lunches": lunches, "dinners": dinners})
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
def customer_meal_history(request, customer_id):
    try:
        customer = get_object_or_404(Customer, _id=ObjectId(customer_id))

        # Get date range: from joining_date to today
        today = datetime.now().date()
        start_date = customer.joining_date
        num_days = (today - start_date).days + 1

        daily_meals = []

        for i in range(num_days):
            current_date = start_date + timedelta(days=i)
            is_weekend = current_date.weekday() >= 5

            # Get meal status for this date
            status = customer.get_status_for_date(current_date)

            daily_meals.append({
                'date': current_date.isoformat(),
                'lunch': status['lunch'],
                'dinner': status['dinner'],
                'is_weekend': is_weekend
            })

        # Calculate statistics
        total_lunches = sum(1 for day in daily_meals if day['lunch'])
        total_dinners = sum(1 for day in daily_meals if day['dinner'])
        total_possible_meals = len(daily_meals) * 2

        response_data = {
            'success': True,
            'customer': {
                'id': str(customer._id),
                'name': customer.name,
                'joining_date': customer.joining_date.isoformat(),
                'fee': float(customer.fee) if hasattr(customer.fee, 'to_decimal') else customer.fee,
            },
            'daily_meals': daily_meals,
            'statistics': {
                'lunches_taken': total_lunches,
                'dinners_taken': total_dinners,
                'total_meals_taken': total_lunches + total_dinners,
                'total_possible_meals': total_possible_meals,
                'completion_rate': round(((total_lunches + total_dinners) / total_possible_meals * 100), 2) if total_possible_meals > 0 else 0
            }
        }

        # Use custom encoder for JSON response
        return Response(response_data)

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)


# Additional utility function to get status for a date range
@api_view(['GET'])
def customer_status_range(request, customer_id):
    try:
        # Use the _id field for MongoDB
        customer = get_object_or_404(Customer, _id=ObjectId(customer_id))
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date', date.today().isoformat())
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else customer.joining_date
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get all statuses in the range
        statuses = {}
        current_date = start_date
        while current_date <= end_date:
            status = customer.get_status_for_date(current_date)
            statuses[current_date.isoformat()] = status
            current_date += timedelta(days=1)
            
        return Response({
            'success': True,
            'customer_id': str(customer_id),  # Convert ObjectId to string
            'customer_name': customer.name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'statuses': statuses
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
def update_specific_date(request):
    """
    Update tiffin status for a specific date and customer
    Expected JSON payload:
    {
        "customer_id": "object_id_string",
        "date": "2024-01-15",
        "lunch": true,
        "dinner": false
    }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_id = data.get('customer_id')
            date_str = data.get('date')
            lunch = data.get('lunch')
            dinner = data.get('dinner')
            
            if not all([customer_id, date_str, lunch is not None, dinner is not None]):
                return JsonResponse({
                    'success': False, 
                    'error': 'Missing required fields: customer_id, date, lunch, dinner'
                }, status=400)
            
            try:
                # Use the _id field for MongoDB
                customer = Customer.objects.get(_id=ObjectId(customer_id))
            except Customer.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'error': 'Customer not found'
                }, status=404)
            
            # Parse the date
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
            
            # Update the status for the specific date
            customer.set_status_for_date(target_date, lunch=lunch, dinner=dinner)
            customer.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Status updated for {target_date}',
                'data': {
                    'customer_id': customer_id,
                    'date': date_str,
                    'lunch': lunch,
                    'dinner': dinner
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'POST method required'}, status=405)


@api_view(['GET'])
def get_date_status(request, customer_id):
    """
    Get tiffin status for a specific date and customer
    URL: /api/customer/<customer_id>/date-status/?date=2024-01-15
    """
    try:
        # Use the _id field for MongoDB
        customer = get_object_or_404(Customer, _id=ObjectId(customer_id))
        date_str = request.GET.get('date')
        
        if not date_str:
            return Response({
                'success': False,
                'error': 'Date parameter is required'
            }, status=400)
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }, status=400)
        
        status = customer.get_status_for_date(target_date)
        
        return Response({
            'success': True,
            'customer_id': customer_id,
            'customer_name': customer.name,
            'date': date_str,
            'status': status
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)