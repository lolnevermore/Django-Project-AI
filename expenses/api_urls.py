from django.urls import path
from .api_views import ExpenseListCreateView, ExpenseDetailView

urlpatterns = [
    path("expenses/", ExpenseListCreateView.as_view(), name="api_expenses"),
    path("expenses/<int:pk>/", ExpenseDetailView.as_view(), name="api_expense_detail"),
]
