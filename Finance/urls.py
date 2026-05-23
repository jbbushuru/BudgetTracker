from django.urls import path
from .views import (
    SMSIngestionView, SMSBatchIngestionView, CategorizeTransactionView, 
    ManualTransactionView, BudgetSummaryView,
    # FinancialGoal views
    FinancialGoalView, FinancialGoalDetailView, TransactionListView,
    # Category CRUD views
    CategoryListView, CategoryDetailView, CategoryLimitView,
)

urlpatterns = [
    # SMS Ingestion: audits one | audits many | lists uncategorized transactions
    path('audit-sms/', SMSIngestionView.as_view(), name='audit_sms'),
    path('audit-sms/batch', SMSBatchIngestionView.as_view(), name='audit_sms_batch'),
    
    # Active Categorization: assigns category during manual entry | allows manual transaction creation | provides summary for dashboard | lists all transactions
    path('categorize/<int:transaction_id>/', CategorizeTransactionView.as_view(), name='categorize_transaction'),
    path('summary/', BudgetSummaryView.as_view(), name='budget_summary'),
    path('limits/', CategoryLimitView.as_view(), name='set_category_limits'),
    
    #Transactions: list | create 
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('manual/', ManualTransactionView.as_view(), name='manual_transaction'),
    
    # Financial Goals: list + create | update + delete (user-owned only)
    path('goals/', FinancialGoalView.as_view(), name='goals_list'),
    path('goals/<int:pk>/', FinancialGoalDetailView.as_view(), name='goal_detail'),

    # Categories: list + create | update + delete (user-owned only)
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),
]