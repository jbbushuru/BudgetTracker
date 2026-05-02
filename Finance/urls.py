from django.urls import path
from .views import SMSIngestionView, CategorizeTransactionView ,ManualTransactionView ,BudgetSummaryView

urlpatterns = [
    # Layer 1: Ingests raw SMS and triggers the AI Auditor
    path('audit-sms/', SMSIngestionView.as_view(), name='audit_sms'),
    
    # Active Categorization: Receives the category selection from the mobile pop-up
    path('categorize/<int:transaction_id>/', CategorizeTransactionView.as_view(), name='categorize_transaction'),
    path('manual/', ManualTransactionView.as_view(), name='manual_transaction'),
    path('summary/', BudgetSummaryView.as_view(), name='budget_summary'),
]