from rest_framework import serializers
from .models import Expense, Category, Budget

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"
