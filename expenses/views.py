import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import ExpenseForm, CategoryForm, BudgetForm, CustomUserCreationForm
from .models import Expense, Category, Budget
from .serializers import ExpenseSerializer
from .utils import account_activation_token



logger = logging.getLogger(__name__)

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Require email confirmation
            user.save()

            # Prepare email data
            current_site = get_current_site(request)
            subject = "Activate your Expense Tracker account"

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            activate_url = f"https://{current_site.domain}/activate/{uid}/{token}/"

            # Plain text version (fallback)
            text_message = f"""
Hi {user.username},

Please click the link below to activate your account:

{activate_url}

If you did not request this, please ignore this email.
"""

            # HTML version
            html_message = render_to_string("expenses/activation_email.html", {
                "user": user,
                "activate_url": activate_url,
            })

            # Send email
            try:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                email.attach_alternative(html_message, "text/html")
                email.send()

                messages.success(request, "Account created! Check your email to activate your account.")
            except Exception as e:
                logger.error(f"Error sending activation email: {e}")
                messages.error(
                    request,
                    "Account created, but we couldn't send the activation email. Contact support."
                )

            return redirect("login")
    else:
        form = CustomUserCreationForm()

    return render(request, "expenses/register.html", {"form": form})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, "Your account has been activated!")
        return redirect("dashboard")
    else:
        messages.error(request, "Activation link is invalid!")
        return redirect("login")

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login')

@login_required
def dashboard(request):
    # Get current month expenses
    today = datetime.now()
    current_month_expenses = Expense.objects.filter(
        user=request.user,
        date__year=today.year,
        date__month=today.month
    )
    
    total_this_month = current_month_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Category breakdown
    category_breakdown = current_month_expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Recent expenses
    recent_expenses = Expense.objects.filter(user=request.user)[:10]
    
    # Monthly trend (last 6 months)
    six_months_ago = today - timedelta(days=180)
    monthly_trend = Expense.objects.filter(
        user=request.user,
        date__gte=six_months_ago
    ).annotate(month=TruncMonth('date')).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    # Budgets
    budgets = Budget.objects.filter(
        user=request.user,
        month__year=today.year,
        month__month=today.month
    )
    
    context = {
        'total_this_month': total_this_month,
        'category_breakdown': category_breakdown,
        'recent_expenses': recent_expenses,
        'monthly_trend': monthly_trend,
        'budgets': budgets,
    }
    return render(request, 'expenses/dashboard.html', context)

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(user=request.user)
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    
    categories = Category.objects.filter(user=request.user)
    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'expenses': expenses,
        'categories': categories,
        'total': total,
    }
    return render(request, 'expenses/expense_list.html', context)

@login_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(user=request.user)
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Add Expense'})

@login_required
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Edit Expense'})

@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expense_list')
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'expenses/category_list.html', {'categories': categories})

@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, 'Category created successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'expenses/category_form.html', {'form': form, 'title': 'Add Category'})

@login_required
def budget_list(request):
    budgets = Budget.objects.filter(user=request.user)
    return render(request, 'expenses/budget_list.html', {'budgets': budgets})

@login_required
def budget_create(request):
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(request, 'Budget created successfully!')
            return redirect('budget_list')
    else:
        form = BudgetForm(user=request.user)
    return render(request, 'expenses/budget_form.html', {'form': form, 'title': 'Add Budget'})


@login_required
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)

    if request.method == 'POST':
        budget.delete()
        return redirect('budget_list')  # Redirect to budgets list after deletion

    return render(request, 'expenses/delete-budget.html', {'budget': budget})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def expense_api(request):
    if request.method == 'GET':
        expenses = Expense.objects.filter(user=request.user)
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    

