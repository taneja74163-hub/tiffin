from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, datetime, timedelta
from django.views.decorators.http import require_GET
from django.http import HttpResponse, JsonResponse
import json
from django.db import transaction
from django.db.models import Q, Count
from django.contrib.auth import authenticate
from calendar import monthrange
import calendar
import io  # ADD THIS IMPORT
from decimal import Decimal  # ADD THIS IMPORT

from .models import Customer, DailyMeal
from django.contrib.auth.models import User

# PDF imports
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from functools import wraps
from rest_framework_simplejwt.authentication import JWTAuthentication
import jwt


# ----------------------------
# Helper functions
# ----------------------------

def jwt_login_required(view_func):
    """
    Custom decorator for JWT authentication in regular Django views
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return JsonResponse({
                'success': False,
                'error': 'Authorization header required'
            }, status=401)
        
        try:
            # Extract token from "Bearer <token>"
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header
            
            # Decode and verify token
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            
            if user and user.is_authenticated:
                request.user = user
                return view_func(request, *args, **kwargs)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid token'
                }, status=401)
                
        except (InvalidToken, AuthenticationFailed, jwt.exceptions.DecodeError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Authentication failed: {str(e)}'
            }, status=401)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Authentication error: {str(e)}'
            }, status=401)
    
    return _wrapped_view

def calculate_total_possible_meals(customer):
    today = date.today()
    total_days_in_month = monthrange(today.year, today.month)[1]
    start_of_month = today.replace(day=1)
    effective_start = max(customer.joining_date, start_of_month)
    active_days = (today - effective_start).days + 1
    
    return {
        "lunches": active_days,
        "dinners": active_days,
        "total_meals": active_days * 2
    }

def serialize_customer(customer):
    return {
        'id': customer.id,
        'name': customer.name,
        'joining_date': customer.joining_date.isoformat(),
        'fee': float(customer.fee),
    }

def update_monthly_cache(customer, target_date):
    """Update cached monthly statistics"""
    today = date.today()
    
    if target_date.year == today.year and target_date.month == today.month:
        month_start = today.replace(day=1)
        
        stats = DailyMeal.objects.filter(
            customer=customer,
            date__gte=month_start,
            date__lte=today
        ).aggregate(
            lunches=Count('id', filter=Q(meal_type='L', is_taken=True)),
            dinners=Count('id', filter=Q(meal_type='D', is_taken=True))
        )
        
        customer.lunches_this_month = stats['lunches'] or 0
        customer.dinners_this_month = stats['dinners'] or 0
        customer.current_month = today.strftime('%Y-%m')
        customer.save()

# ----------------------------
# Authentication APIs (JWT)
# ----------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """User registration with JWT token response"""
    try:
        data = request.data
        username = data.get("username")
        password = data.get("password")
        email = data.get("email", "")

        if not username or not password:
            return Response({"error": "Username and password required"}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=400)

        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password
        )
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "User created successfully",
            "user_id": user.id,
            "username": user.username,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """User login with JWT token response"""
    try:
        data = request.data
        username = data.get("username")
        password = data.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response({"error": "Invalid credentials"}, status=401)

        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "Login successful",
            "user_id": user.id,
            "username": user.username,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })

    except Exception as e:
        return Response({"error": str(e)}, status=400)

# ----------------------------
# Home & Customer List
# ----------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def home(request):
    """API documentation endpoint"""
    return Response({
        "message": "Tiffin Service API",
        "status": "OK",
        "endpoints": {
            "signup": "POST /api/signup/",
            "login": "POST /api/login/",
            "add_customer": "POST /api/add_customer/",
            "list_customers": "GET /api/hello/",
            "customer_detail": "GET /api/customer/<id>/",
            "update_status": "POST /api/update_specific_date/",
            "date_status": "GET /api/customer/<id>/date-status/?date=YYYY-MM-DD",
            "generate_pdf": "GET /api/customer/<id>/pdf/?month=YYYY-MM",
            "download_pdf": "GET /api/customer/<id>/download-pdf/?month=YYYY-MM",
            "jwt_token": "POST /api/token/",
            "jwt_refresh": "POST /api/token/refresh/",
            "jwt_verify": "POST /api/token/verify/"
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hello(request):
    """Get all customers with today's status"""
    try:
        today = date.today()
        customers = Customer.objects.filter(user=request.user)
        
        result = []
        for customer in customers:
            meals = DailyMeal.objects.filter(customer=customer, date=today)
            
            lunch = True
            dinner = True
            
            for meal in meals:
                if meal.meal_type == 'L':
                    lunch = meal.is_taken
                elif meal.meal_type == 'D':
                    dinner = meal.is_taken
            
            result.append({
                'id': customer.id,
                'name': customer.name,
                'lunch': lunch,
                'dinner': dinner
            })
        
        return Response({"customers": result})
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)

# ----------------------------
# Customer CRUD Operations
# ----------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def add_customer(request):
    """Create a new customer"""
    try:            
        data = request.data
        customer = Customer.objects.create(
            user=request.user,
            name=data.get('name'),
            joining_date=data.get('joining_date', date.today()),
            fee=data.get('fee', 0.0),
            current_month=date.today().strftime('%Y-%m')
        )
        
        # Create today's meal records
        today = date.today()
        DailyMeal.objects.bulk_create([
            DailyMeal(customer=customer, date=today, meal_type='L', is_taken=True),
            DailyMeal(customer=customer, date=today, meal_type='D', is_taken=True)
        ])
        
        return Response({'success': True, 'id': customer.id})
        
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=400)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_customer(request, id):
    """Edit customer details"""
    try:
        customer = get_object_or_404(Customer, id=id, user=request.user)
        data = request.data
        
        customer.name = data.get('name', customer.name)
        
        # Update joining_date if provided
        joining_date_str = data.get('joining_date')
        if joining_date_str:
            customer.joining_date = datetime.strptime(joining_date_str, '%Y-%m-%d').date()
        
        # Update fee if provided
        fee = data.get('fee')
        if fee is not None:
            customer.fee = fee
            
        customer.save()
        return Response({'success': True})
        
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_customer(request, customer_id):
    """Delete a customer"""
    customer = get_object_or_404(Customer, id=customer_id, user=request.user)
    customer.delete()

    return Response({"success": True, "message": "Customer deleted"})

# ----------------------------
# Customer Details & Stats
# ----------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_detail(request, id):
    """Get customer details with today's status"""
    try:
        customer = get_object_or_404(Customer, id=id, user=request.user)
        data = serialize_customer(customer)
        
        # Add today's status
        today = date.today()
        meals = DailyMeal.objects.filter(customer=customer, date=today)
        
        lunch = True
        dinner = True
        
        for meal in meals:
            if meal.meal_type == 'L':
                lunch = meal.is_taken
            elif meal.meal_type == 'D':
                dinner = meal.is_taken
        
        data['today_status'] = {
            'lunch': lunch,
            'dinner': dinner,
            'date': today.isoformat()
        }
        
        return Response(data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_stats(request, id):
    """Get customer statistics for current month"""
    try:
        customer = get_object_or_404(Customer, id=id, user=request.user)
        today = date.today()

        days_in_month = monthrange(today.year, today.month)[1]
        start_of_month = today.replace(day=1)

        effective_start = max(customer.joining_date, start_of_month)
        active_days = max(0, (today - effective_start).days + 1)

        total_lunch_possible = active_days
        total_dinner_possible = active_days

        missed_stats = DailyMeal.objects.filter(
            customer=customer,
            date__gte=start_of_month,
            date__lte=today,
            is_taken=False
        ).aggregate(
            lunch_missed=Count('id', filter=Q(meal_type='L')),
            dinner_missed=Count('id', filter=Q(meal_type='D'))
        )

        lunch_missed = missed_stats.get("lunch_missed") or 0
        dinner_missed = missed_stats.get("dinner_missed") or 0

        lunches_taken = total_lunch_possible - lunch_missed
        dinners_taken = total_dinner_possible - dinner_missed

        return Response({
            "success": True,
            "month": today.strftime("%Y-%m"),
            "lunches_taken": int(lunches_taken),
            "dinners_taken": int(dinners_taken),
            "lunches_missed": int(lunch_missed),
            "dinners_missed": int(dinner_missed),
            "total_lunch_possible": int(total_lunch_possible),
            "total_dinner_possible": int(total_dinner_possible),
        })

    except Exception as e:
        return Response({'error': str(e)}, status=400)

# ----------------------------
# Meal Management
# ----------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_tiffin(request):
    """Mark tiffin status for a specific slot"""
    try:
        data = request.data
        customer_id = data.get('customer_id')
        slot = data.get('slot')  # 'lunch' or 'dinner'
        value = data.get('value', True)
        date_str = data.get('date', date.today().isoformat())
        
        customer = get_object_or_404(Customer, id=customer_id, user=request.user)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        meal_type = 'L' if slot == 'lunch' else 'D'
        
        DailyMeal.objects.update_or_create(
            customer=customer,
            date=target_date,
            meal_type=meal_type,
            defaults={'is_taken': value}
        )
        
        update_monthly_cache(customer, target_date)
        
        return Response({'success': True})
        
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_specific_date(request):
    """Update meal status for a specific date"""
    try:
        data = request.data
        customer_id = data.get("customer_id")
        date_str = data.get("date")
        lunch = data.get("lunch", True)
        dinner = data.get("dinner", True)

        customer = Customer.objects.get(id=customer_id, user=request.user)
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Lunch
        if lunch:
            DailyMeal.objects.filter(
                customer=customer,
                date=target_date,
                meal_type="L"
            ).delete()
        else:
            DailyMeal.objects.update_or_create(
                customer=customer,
                date=target_date,
                meal_type="L",
                defaults={"is_taken": False},
            )

        # Dinner
        if dinner:
            DailyMeal.objects.filter(
                customer=customer,
                date=target_date,
                meal_type="D"
            ).delete()
        else:
            DailyMeal.objects.update_or_create(
                customer=customer,
                date=target_date,
                meal_type="D",
                defaults={"is_taken": False},
            )

        return Response({
            "success": True,
            "message": f"Updated status for {date_str}",
        })

    except Customer.DoesNotExist:
        return Response({"success": False, "error": "Customer not found"}, status=404)
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_date_status(request, customer_id):
    """Get meal status for a specific date"""
    try:
        customer = get_object_or_404(Customer, id=customer_id, user=request.user)
        date_str = request.GET.get('date')
        
        if not date_str:
            return Response({
                'success': False,
                'error': 'Date parameter is required'
            }, status=400)
        
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        meals = DailyMeal.objects.filter(customer=customer, date=target_date)
        
        lunch = True
        dinner = True
        
        for meal in meals:
            if meal.meal_type == 'L':
                lunch = meal.is_taken
            elif meal.meal_type == 'D':
                dinner = meal.is_taken
        
        return Response({
            'success': True,
            'customer_id': customer_id,
            'customer_name': customer.name,
            'date': date_str,
            'status': {'lunch': lunch, 'dinner': dinner}
        })
        
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_meal_history(request, customer_id):
    """Get meal history for a customer"""
    try:
        customer = get_object_or_404(Customer, id=customer_id, user=request.user)
        
        # Get date range
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date', date.today().isoformat())
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = customer.joining_date
            
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get meals in date range
        meals = DailyMeal.objects.filter(
            customer=customer,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('-date', 'meal_type')
        
        # Group by date
        daily_data = {}
        for meal in meals:
            date_key = meal.date.isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'date': date_key,
                    'lunch': True,
                    'dinner': True,
                    'is_weekend': meal.date.weekday() >= 5
                }
            
            if meal.meal_type == 'L':
                daily_data[date_key]['lunch'] = meal.is_taken
            elif meal.meal_type == 'D':
                daily_data[date_key]['dinner'] = meal.is_taken
        
        daily_meals = list(daily_data.values())
        
        # Calculate stats
        total_days = (end_date - start_date).days + 1
        total_lunches = sum(1 for day in daily_meals if day['lunch'])
        total_dinners = sum(1 for day in daily_meals if day['dinner'])
        total_possible_meals = total_days * 2
        
        return Response({
            'success': True,
            'customer': serialize_customer(customer),
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
        return Response({'success': False, 'error': str(e)}, status=400)

# ----------------------------
# PDF Generation
# ----------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_customer_pdf(request, customer_id):
    """Generate PDF report for a customer for selected month - DRF API version"""
    try:
        customer = get_object_or_404(Customer, id=customer_id, user=request.user)
        
        # Get month from query parameters (default to current month)
        month = request.GET.get('month')
        if month:
            year, month_num = map(int, month.split('-'))
        else:
            today = date.today()
            year, month_num = today.year, today.month
        
        # Calculate date range for the selected month
        _, last_day = monthrange(year, month_num)
        start_date = date(year, month_num, 1)
        end_date = date(year, month_num, last_day)
        
        # If customer joined after month start, adjust start date
        if customer.joining_date > start_date:
            start_date = customer.joining_date
        
        # Get all meals for the month
        meals = DailyMeal.objects.filter(
            customer=customer,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date', 'meal_type')
        
        # Organize data by date
        meal_dict = {}
        for meal in meals:
            date_key = meal.date
            if date_key not in meal_dict:
                meal_dict[date_key] = {'lunch': True, 'dinner': True}
            
            if meal.meal_type == 'L':
                meal_dict[date_key]['lunch'] = meal.is_taken
            elif meal.meal_type == 'D':
                meal_dict[date_key]['dinner'] = meal.is_taken
        
        # Calculate statistics
        active_days = (end_date - start_date).days + 1
        
        # Calculate taken and missed meals
        lunches_taken = sum(1 for day_data in meal_dict.values() if day_data['lunch'])
        dinners_taken = sum(1 for day_data in meal_dict.values() if day_data['dinner'])
        
        lunches_missed = active_days - lunches_taken
        dinners_missed = active_days - dinners_taken
        
        # Calculate total fee for the month - FIXED
        total_meals_taken = lunches_taken + dinners_taken
        total_possible_meals = active_days * 2
        
        # Fix the Decimal calculation error
        if total_possible_meals > 0:
            # Convert to float for calculation
            proportion_taken = total_meals_taken / total_possible_meals
            amount_payable = float(proportion_taken * float(customer.fee))
        else:
            amount_payable = 0.0
        
        # Create PDF in memory
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        # PDF content
        y_position = 750
        
        # Title
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(200, y_position, "Tiffin Service Monthly Report")
        y_position -= 30
        
        # Customer Information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y_position, f"Customer: {customer.name}")
        y_position -= 20
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, y_position, f"Month: {calendar.month_name[month_num]} {year}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Joining Date: {customer.joining_date.strftime('%d %B %Y')}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Monthly Fee: ₹{float(customer.fee):.2f}")
        y_position -= 40
        
        # Summary Statistics
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y_position, "Monthly Summary")
        y_position -= 30
        
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, y_position, f"Active Days in Month: {active_days}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Lunches Taken: {lunches_taken} / {active_days}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Dinners Taken: {dinners_taken} / {active_days}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Total Meals Taken: {total_meals_taken} / {total_possible_meals}")
        y_position -= 20
        
        # Fix completion rate calculation
        completion_rate = (total_meals_taken / total_possible_meals * 100) if total_possible_meals > 0 else 0
        pdf.drawString(50, y_position, f"Meal Completion Rate: {completion_rate:.1f}%")
        y_position -= 20
        
        pdf.drawString(50, y_position, f"Amount Payable: ₹{amount_payable:.2f}")
        y_position -= 40
        
        # Daily Meal Table
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y_position, "Daily Meal Status")
        y_position -= 30
        
        # Create table data
        table_data = [['Date', 'Day', 'Lunch', 'Dinner', 'Status']]
        
        # Add rows for each day
        current_date = start_date
        while current_date <= end_date:
            day_name = calendar.day_name[current_date.weekday()]
            meal_status = meal_dict.get(current_date, {'lunch': True, 'dinner': True})
            
            lunch_status = "✓" if meal_status['lunch'] else "✗"
            dinner_status = "✓" if meal_status['dinner'] else "✗"
            
            day_status = "Present" if meal_status['lunch'] or meal_status['dinner'] else "Absent"
            
            table_data.append([
                current_date.strftime('%d-%m-%Y'),
                day_name[:3],
                lunch_status,
                dinner_status,
                day_status
            ])
            
            current_date += timedelta(days=1)
        
        # Create and style table
        table = Table(table_data, colWidths=[80, 50, 50, 50, 60])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Draw table
        table.wrapOn(pdf, 400, 200)
        table.drawOn(pdf, 50, y_position - (len(table_data) * 20) - 20)
        
        # Footer
        pdf.setFont("Helvetica-Oblique", 10)
        pdf.drawString(50, 50, f"Report generated on {date.today().strftime('%d %B %Y')}")
        pdf.drawString(50, 35, "Signature: ________________________")
        
        pdf.showPage()
        pdf.save()
        
        # Get PDF value from buffer
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create HTTP response
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{customer.name}_{year}_{month_num}_report.pdf"'
        return response
        
    except Exception as e:
        # Return JSON error for debugging
        return Response({'success': False, 'error': str(e)}, status=400)

@require_GET
@jwt_login_required 
def download_customer_pdf(request, customer_id):
    """PDF download view (regular Django view with JWT auth)"""
    try:
        customer = get_object_or_404(Customer, id=customer_id, user=request.user)
        
        # Get month from query parameters
        month = request.GET.get('month')
        if month:
            year, month_num = map(int, month.split('-'))
        else:
            today = date.today()
            year, month_num = today.year, today.month
        
        # Calculate date range for the selected month
        _, last_day = monthrange(year, month_num)
        start_date = date(year, month_num, 1)
        end_date = date(year, month_num, last_day)
        
        # If customer joined after month start, adjust start date
        if customer.joining_date > start_date:
            start_date = customer.joining_date
        
        # Get all meals for the month
        meals = DailyMeal.objects.filter(
            customer=customer,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date', 'meal_type')
        
        # Organize data by date
        meal_dict = {}
        for meal in meals:
            date_key = meal.date
            if date_key not in meal_dict:
                meal_dict[date_key] = {'lunch': True, 'dinner': True}
            
            if meal.meal_type == 'L':
                meal_dict[date_key]['lunch'] = meal.is_taken
            elif meal.meal_type == 'D':
                meal_dict[date_key]['dinner'] = meal.is_taken
        
        # Calculate statistics
        active_days = (end_date - start_date).days + 1
        
        # Calculate taken and missed meals
        lunches_taken = sum(1 for day_data in meal_dict.values() if day_data['lunch'])
        dinners_taken = sum(1 for day_data in meal_dict.values() if day_data['dinner'])
        
        lunches_missed = active_days - lunches_taken
        dinners_missed = active_days - dinners_taken
        
        # Calculate total fee for the month - FIXED
        total_meals_taken = lunches_taken + dinners_taken
        total_possible_meals = active_days * 2
        
        # Fix the Decimal calculation error
        if total_possible_meals > 0:
            # Convert to float for calculation
            proportion_taken = total_meals_taken / total_possible_meals
            amount_payable = float(proportion_taken * float(customer.fee))
        else:
            amount_payable = 0.0
        
        # Create PDF
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        # PDF content
        y_position = 750
        
        # Title
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(200, y_position, "Tiffin Service Monthly Report")
        y_position -= 30
        
        # Customer Information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y_position, f"Customer: {customer.name}")
        y_position -= 20
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, y_position, f"Month: {calendar.month_name[month_num]} {year}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Joining Date: {customer.joining_date.strftime('%d %B %Y')}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Monthly Fee: ₹{float(customer.fee):.2f}")
        y_position -= 40
        
        # Summary Statistics
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y_position, "Monthly Summary")
        y_position -= 30
        
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, y_position, f"Active Days in Month: {active_days}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Lunches Taken: {lunches_taken} / {active_days}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Dinners Taken: {dinners_taken} / {active_days}")
        y_position -= 20
        pdf.drawString(50, y_position, f"Total Meals Taken: {total_meals_taken} / {total_possible_meals}")
        y_position -= 20
        
        # Fix completion rate calculation
        completion_rate = (total_meals_taken / total_possible_meals * 100) if total_possible_meals > 0 else 0
        pdf.drawString(50, y_position, f"Meal Completion Rate: {completion_rate:.1f}%")
        y_position -= 20
        
        pdf.drawString(50, y_position, f"Amount Payable: ₹{amount_payable:.2f}")
        y_position -= 40
        
        # Daily Meal Table
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y_position, "Daily Meal Status")
        y_position -= 30
        
        # Create table data
        table_data = [['Date', 'Day', 'Lunch', 'Dinner', 'Status']]
        
        # Add rows for each day
        current_date = start_date
        while current_date <= end_date:
            day_name = calendar.day_name[current_date.weekday()]
            meal_status = meal_dict.get(current_date, {'lunch': True, 'dinner': True})
            
            lunch_status = "✓" if meal_status['lunch'] else "✗"
            dinner_status = "✓" if meal_status['dinner'] else "✗"
            day_status = "Present" if meal_status['lunch'] or meal_status['dinner'] else "Absent"
            
            table_data.append([
                current_date.strftime('%d-%m-%Y'),
                day_name[:3],
                lunch_status,
                dinner_status,
                day_status
            ])
            
            current_date += timedelta(days=1)
        
        table = Table(table_data, colWidths=[80, 50, 50, 50, 60])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        table.wrapOn(pdf, 400, 200)
        table.drawOn(pdf, 50, y_position - (len(table_data) * 20) - 20)
        
        # Footer
        pdf.setFont("Helvetica-Oblique", 10)
        pdf.drawString(50, 50, f"Report generated on {date.today().strftime('%d %B %Y')}")
        pdf.drawString(50, 35, "Signature: ________________________")
        
        pdf.showPage()
        pdf.save()
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{customer.name}_{year}_{month_num}_report.pdf"'
        return response
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)