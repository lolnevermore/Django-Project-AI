from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from .models import Expense, Category, Budget
from .forms import ExpenseForm, CategoryForm, BudgetForm

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'expenses/register.html', {'form': form})

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