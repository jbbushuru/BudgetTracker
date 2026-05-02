from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Transaction
from .models import Category
from .ai_parser import SMSParserService
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal

class SMSIngestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_sms = request.data.get('sms_text')
        
        if not raw_sms:
            return Response({"error": "No SMS text provided"}, status=400)

        # 1. AI Auditor determines IN/OUT and strips the data
        parser = SMSParserService()
        audit_result = parser.parse_mpesa_sms(raw_sms)

        if not audit_result:
            return Response({"error": "Failed to audit data"}, status=500)

        # 2. Create the transaction record
        try:
            transaction = Transaction.objects.create(
                user=request.user,
                source='MPESA',
                transaction_type=audit_result.get('transaction_type', 'OUT'),
                sms_batch=raw_sms,
                amount=audit_result.get('amount'),
                fee=audit_result.get('fee', 0.00),
                recipient=audit_result.get('recipient'),
                is_pending_categorization=True
            )
            return Response({
                "needs_categorization": transaction.is_pending_categorization,
                "transaction_id": transaction.id,
                "type": transaction.transaction_type,
                "amount": transaction.amount,
                "entity": transaction.recipient,  
                "push_message": f"How would you categorize {transaction.amount} KES {'from' if transaction.transaction_type == 'IN' else 'to'} {transaction.recipient}?"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

class CategorizeTransactionView(APIView):
    """
    The endpoint called when a user clicks a category button in the pop-up or app.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, transaction_id):
        category_id = request.data.get('category_id')
        
        if not category_id:
            return Response({"error": "category_id is required"}, status=400)

        try:
            # Ensure the transaction belongs to the logged-in user
            transaction = Transaction.objects.get(id=transaction_id, user=request.user)
            
            # Retrieve the chosen category
            category = Category.objects.get(id=category_id)
            
            # Update the transaction
            transaction.category = category
            transaction.is_pending_categorization = False 
            transaction.save()
            
            return Response({
                "status": "success",
                "message": f"Transaction marked as {category.name}",
                "transaction_id": transaction.id
            }, status=status.HTTP_200_OK)

        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found or unauthorized"}, status=404)
        except Category.DoesNotExist:
            return Response({"error": "Invalid category ID"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
class ManualTransactionView(APIView):
    """
    POST: Handles manual entry of CASH or BANK transactions.
    Endpoint: /finance/manual/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        
        # 1. Extraction with fallbacks
        amount = data.get('amount')
        t_type = data.get('transaction_type', 'OUT') # IN or OUT
        source = data.get('source', 'CASH')          # CASH or BANK
        recipient = data.get('recipient', 'General')
        category_id = data.get('category_id')

        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 2. Category Lookup (Optional for manual entry)
            category = None
            if category_id:
                category = Category.objects.get(id=category_id)

            # 3. Create the record
            # is_pending_categorization is False because the user provides the category now
            transaction = Transaction.objects.create(
                user=request.user,
                source=source,
                transaction_type=t_type,
                amount=amount,
                recipient=recipient,
                category=category,
                is_pending_categorization=False if category else True
            )

            return Response({
                "message": "Transaction logged successfully",
                "transaction_id": transaction.id, # Uses the auto-generated ID
                "status": "categorized" if category else "pending"
            }, status=status.HTTP_201_CREATED)

        except Category.DoesNotExist:
            return Response({"error": "Invalid category_id"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
class BudgetSummaryView(APIView):
    """
    GET: Returns total spent, remaining balance, and a breakdown per category.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.profile  # Accessed directly via OneToOne relationship
        
        # 1. Define current month range
        now = timezone.now()
        
        # 2. Total Spent this month (OUT transactions)
        total_spent = Transaction.objects.filter(
            user=user,
            transaction_type='OUT',
            timestamp__month=now.month,
            timestamp__year=now.year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # 3. Total Received this month (IN transactions)
        total_received = Transaction.objects.filter(
            user=user,
            transaction_type='IN',
            timestamp__month=now.month,
            timestamp__year=now.year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # 4. Calculation Logic
        # We use the monthly_income you've stored in your Profile
        monthly_income = profile.monthly_income
        remaining_budget = (monthly_income + total_received) - total_spent

        # 5. Spent Per Category breakdown
        # We group by the category name and sum the amounts
        category_breakdown = Transaction.objects.filter(
            user=user,
            transaction_type='OUT',
            timestamp__month=now.month,
            timestamp__year=now.year
        ).values(
            'category__name', 
            'category__icon_name', 
            'category__is_essential'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('-total_amount')

        return Response({
            "month": now.strftime("%B %Y"),
            "summary": {
                "income_baseline": float(monthly_income),
                "total_received": float(total_received),
                "total_spent": float(total_spent),
                "remaining_balance": float(remaining_budget)
            },
            "category_spending": [
                {
                    "category": item['category__name'] or "Uncategorized",
                    "icon": item['category__icon_name'],
                    "is_essential": item['category__is_essential'],
                    "amount_spent": float(item['total_amount'])
                } for item in category_breakdown
            ]
        })