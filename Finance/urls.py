from django.urls import path
#added the Batch ingestion logic in imports
from .views import SMSIngestionView, SMSBatchIngestionView, CategorizeTransactionView, ManualTransactionView, BudgetSummaryView, PendingTransactionsView

urlpatterns = [
    # Layer 1: Ingests raw SMS and triggers the AI Auditor
    path('audit-sms/', SMSIngestionView.as_view(), name='audit_sms'),
    #added a path for the batch processing
    path('audit-sms/batch', SMSBatchIngestionView.as_view(), name='audit_sms_batch'),
    # added a path that returns pending transactions to the app to fetch them for the transaction view
    path('pending/', PendingTransactionsView.as_view(), name='pending_transactions'),
    
    # Active Categorization: Receives the category selection from the mobile pop-up
    path('categorize/<int:transaction_id>/', CategorizeTransactionView.as_view(), name='categorize_transaction'),
    path('manual/', ManualTransactionView.as_view(), name='manual_transaction'),
    path('summary/', BudgetSummaryView.as_view(), name='budget_summary'),
]