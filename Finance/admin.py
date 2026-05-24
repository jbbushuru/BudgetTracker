from django.contrib import admin

from .models import Category, Transaction, FinancialGoal, CategoryLimit

admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(FinancialGoal)
admin.site.register(CategoryLimit)
