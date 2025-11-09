from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.description} - ${self.amount}"


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.DateField(null=True, blank=True)  # Allow null months
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'category', 'month']
        ordering = ['-month']
    
    def __str__(self):
        if self.month:
            return f"{self.category.name} - ${self.amount} ({self.month.strftime('%B %Y')})"
        return f"{self.category.name} - ${self.amount} (No month set)"
    
    def get_spent_amount(self):
        if not self.month:
            return 0  # Safe fallback if month is None
        total = Expense.objects.filter(
            user=self.user,
            category=self.category,
            date__year=self.month.year,
            date__month=self.month.month
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        return total
    
    def get_remaining(self):
        return self.amount - self.get_spent_amount()
