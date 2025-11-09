from django.contrib import admin
from .models import Category, Expense, Budget

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    list_filter = ['user', 'created_at']
    search_fields = ['name', 'description']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'category', 'user', 'date', 'payment_method']
    list_filter = ['category', 'payment_method', 'date', 'user']
    search_fields = ['description', 'notes']
    date_hierarchy = 'date'

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'month', 'user', 'get_spent_amount', 'get_remaining']
    list_filter = ['month', 'user', 'category']