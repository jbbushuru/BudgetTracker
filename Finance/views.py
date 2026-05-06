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

# added a function to handle processing of a single transaction. 
# I separated this part from the initial SMSIngestionView to prevent duplicate code for Batch processing
def process_single_transaction(user, raw_sms, audit_result):
    """
    Handles categorization and database creation.
    Priority: 1. User History (Smart Match) -> 2. AI Suggestion -> 3. Pending
    """
    # 1. Look for a previous category for this recipient (Smart Match)
    existing_category_id = Transaction.objects.filter(
        user=user, 
        recipient=audit_result.get('recipient'),
        is_pending_categorization=False
    ).order_by('-timestamp').values_list('category_id', flat=True).first()

    # 2. If no history, use the AI's suggested category
    ai_category_id = None
    if not existing_category_id and 'suggested_category' in audit_result:
        ai_category_id = Category.objects.filter(
            name=audit_result['suggested_category']
        ).values_list('id', flat=True).first()

    final_category_id = existing_category_id or ai_category_id

    return Transaction.objects.create(
        user=user,
        source='MPESA',
        transaction_type=audit_result.get('transaction_type', 'OUT'),
        sms_batch=raw_sms,
        amount=audit_result.get('amount'),
        fee=audit_result.get('fee', 0.00),
        recipient=audit_result.get('recipient'),
        category_id=final_category_id,
        is_pending_categorization=False if final_category_id else True
    )

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

        # 2. Process and save using shared logic (includes Smart Matching)
        try:
            #creation of a transaction done hear using the function i "added" in line 17
            transaction = process_single_transaction(request.user, raw_sms, audit_result)
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

#added logic to handle SMS batches
class SMSBatchIngestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        transactions_data = request.data.get('transactions', [])
        
        if not transactions_data:
            return Response({"error": "No transactions provided"}, status=400)

        parser = SMSParserService()
        processed_count = 0
        errors = []

        # 1. FAST-TRACK: Filter out transactions we can categorize via keywords
        remaining_sms = []
        for item in transactions_data:
            raw_sms = item.get('body')
            if not raw_sms:
                continue

            category_name = parser.keyword_categorizer.get_category(raw_sms)
            audit_result = parser.keyword_categorizer.extract_basic_info(raw_sms) if category_name else None

            if category_name and audit_result:
                try:
                    category = Category.objects.filter(name=category_name).first()
                    
                    Transaction.objects.create(
                        user=request.user,
                        source='MPESA',
                        transaction_type=audit_result.get('transaction_type', 'OUT'),
                        sms_batch=raw_sms,
                        amount=audit_result.get('amount'),
                        fee=0.0,
                        recipient=audit_result.get('recipient'),
                        category=category,
                        is_pending_categorization=False
                    )
                    processed_count += 1
                except Exception as e:
                    errors.append(f"Fast-track error: {str(e)}")
            else:
                remaining_sms.append(raw_sms)

        # 2. AI BATCH: Process only the unknown transactions in chunks
        if remaining_sms:
            CHUNK_SIZE = 10
            for i in range(0, len(remaining_sms), CHUNK_SIZE):
                # Safety delay to stay under the tight 5-15 RPM limit
                if i > 0:
                    import time
                    time.sleep(2)

                chunk_texts = remaining_sms[i:i + CHUNK_SIZE]
                audit_results = parser.parse_mpesa_batch(chunk_texts)

                for raw_sms, audit_result in zip(chunk_texts, audit_results):
                    if not audit_result or not audit_result.get('recipient'):
                        errors.append(f"Failed to parse: {raw_sms[:20]}...")
                        continue

                    try:
                        process_single_transaction(request.user, raw_sms, audit_result)
                        processed_count += 1
                    except Exception as e:
                        errors.append(str(e))

        return Response({
            "processed_count": processed_count,
            "fast_tracked": processed_count - len([e for e in errors if "Failed to parse" in e]), # Approximate
            "errors": errors
        }, status=status.HTTP_201_CREATED)

class PendingTransactionsView(APIView):
    """
    GET: Returns all transactions that need categorization for the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pending = Transaction.objects.filter(
            user=request.user, 
            is_pending_categorization=True
        ).order_by('-timestamp')
        
        data = [{
            "id": t.id,
            "amount": float(t.amount),
            "recipient": t.recipient,
            "timestamp": t.timestamp,
            "type": t.transaction_type
        } for t in pending]
        
        return Response(data)

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
        #used the budget field i added to calculate available balance.
        remaining_budget = (profile.budget) - total_spent

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
            #added color code as a field returned
            'category__color_code',
            'category__is_essential'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('-total_amount')

        return Response({
            "month": now.strftime("%B %Y"),
            "summary": {
                #made budget the income baseline.
                "income_baseline": float(profile.budget),
                "total_received": float(total_received),
                "total_spent": float(total_spent),
                "remaining_balance": float(remaining_budget)
            },
            "category_spending": [
                {
                    "category": item['category__name'] or "Uncategorized",
                    "icon": item['category__icon_name'],
                    #added colo code to be sent as part of the response
                    "color": item['category__color_code'] or "#94A3B8",
                    "is_essential": item['category__is_essential'],
                    "amount_spent": float(item['total_amount'])
                } for item in category_breakdown
            ]
        })