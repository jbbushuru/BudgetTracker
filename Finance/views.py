from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
# imported additional CategorySerializer
from .models import Transaction, Category, FinancialGoal
from .serializers import CategorySerializer, FinancialGoalSerializer, TransactionSerializer
from .ai_parser import SMSParserService
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------
class CategoryListView(APIView):
    """
    GET:  Returns all categories visible to the user
          (system-wide categories where owner=None, plus the user's own).
    POST: Creates a new user-owned category.
    Endpoint: /finance/categories/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = Category.objects.filter(
            Q(owner=None) | Q(owner=request.user)
        ).order_by('name')
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            # Force the owner to be the authenticated user — no spoofing
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryDetailView(APIView):
    """
    PATCH:  Updates a user-owned category (system categories cannot be edited).
    DELETE: Deletes a user-owned category (system categories cannot be deleted).
    Endpoint: /finance/categories/<int:pk>/
    """
    permission_classes = [IsAuthenticated]

    def _get_user_category(self, pk, user):
        """
        Helper: Fetch a category that belongs to this user.
        Returns (category, error_response).
        """
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return None, Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

        # System categories have owner=None — no one can modify them
        if category.owner is None:
            return None, Response(
                {"error": "System categories cannot be modified or deleted"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Users can only modify their own categories
        if category.owner != user:
            return None, Response(
                {"error": "You do not have permission to modify this category"},
                status=status.HTTP_403_FORBIDDEN
            )

        return category, None

    def patch(self, request, pk):
        category, error = self._get_user_category(pk, request.user)
        if error:
            return error

        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        category, error = self._get_user_category(pk, request.user)
        if error:
            return error

        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
# ---------------------------------------------------------------------------


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
        timestamp=audit_result.get('timestamp'),
        is_pending_categorization=False if final_category_id else True
    )

class SMSIngestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Support both 'sms_text' and 'body' for flexibility
        raw_sms = request.data.get('sms_text') or request.data.get('body')
        
        if not raw_sms:
            return Response({"error": "No SMS text provided"}, status=400)

        # 1. AI Auditor determines IN/OUT and strips the data
        parser = SMSParserService()
        audit_result = parser.parse_mpesa_sms(raw_sms, user=request.user)

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

        # All transactions are now handled by the AI to ensure accurate parsing of dates/amounts
        all_sms = [item.get('body') for item in transactions_data if item.get('body')]
        
        if all_sms:
            CHUNK_SIZE = 30
            for i in range(0, len(all_sms), CHUNK_SIZE):
                if i > 0:
                    import time
                    time.sleep(1) # RPM limit safety

                chunk_texts = all_sms[i:i + CHUNK_SIZE]
                audit_results = parser.parse_mpesa_batch(chunk_texts, user=request.user)

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

        # 6. Weekly Spend (Monday to Today)
        current_time = timezone.localtime(timezone.now())
        days_since_monday = current_time.weekday()
        monday_date = (current_time - timedelta(days=days_since_monday)).date()
        
        weekly_spend = []
        for i in range(days_since_monday + 1):
            day_date = monday_date + timedelta(days=i)
            day_total = Transaction.objects.filter(
                user=user,
                transaction_type='OUT',
                timestamp__date=day_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            weekly_spend.append(float(day_total))

        return Response({
            "month": now.strftime("%B %Y"),
            "summary": {
                #made budget the income baseline.
                "income_baseline": float(profile.budget),
                "total_received": float(total_received),
                "total_spent": float(total_spent),
                "remaining_balance": float(remaining_budget),
                "weekly_spend": weekly_spend
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

# I implemented standard RESTful endpoints for the goals:
# GET /api/finance/goals/: Fetch all goals for the user.
# POST /api/finance/goals/: Create a new goal.
# PATCH /api/finance/goals/<id>/: Update a goal (e.g., adding savings).
# DELETE /api/finance/goals/<id>/: Remove a goal.
class FinancialGoalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        goals = FinancialGoal.objects.filter(user=request.user).order_by('-created_at')
        serializer = FinancialGoalSerializer(goals, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FinancialGoalSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FinancialGoalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            goal = FinancialGoal.objects.get(pk=pk, user=request.user)
            serializer = FinancialGoalSerializer(goal, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except FinancialGoal.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class TransactionListView(APIView):
    """
    GET: Returns a paginated list of transactions, with optional month/year filtering.
    Endpoint: /finance/transactions/?month=5&year=2026&page=1
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        # Base Queryset
        queryset = Transaction.objects.filter(user=user).order_by('-timestamp')
        
        # Filtering by date if provided
        if month:
            queryset = queryset.filter(timestamp__month=month)
        if year:
            queryset = queryset.filter(timestamp__year=year)
            
        # Basic Manual Pagination
        page_size = 20
        try:
            page = int(request.query_params.get('page', 1))
        except ValueError:
            page = 1
            
        start = (page - 1) * page_size
        end = start + page_size
        
        transactions = queryset[start:end]
        serializer = TransactionSerializer(transactions, many=True)
        
        return Response({
            "transactions": serializer.data,
            "has_next": queryset.count() > end,
            "page": page,
            "total_count": queryset.count()
        })

    def delete(self, request, pk):
        try:
            goal = FinancialGoal.objects.get(pk=pk, user=request.user)
            goal.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FinancialGoal.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)