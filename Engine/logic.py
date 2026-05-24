# src/Engine/logic.py
from django.db.models import Sum, Q
from django.utils import timezone
from Finance.models import Transaction
from Users.models import Profile
from .models import RuleMetadata
from decimal import Decimal

def get_active_triggers(user):
    """
    Scans the user's monthly data against defined rules.
    Returns a list of trigger strings for the AI Advisor to process.
    """
    triggers = []
    
    try:
        profile = Profile.objects.get(user=user)
        income = profile.monthly_income
        
        # Guard: If no income is set, we can't calculate percentages
        if not income or income <= 0:
            return ["NO_INCOME_SET"]

        # 1. Fetch relevant rules (Global rules + User-specific overrides)
        rules = RuleMetadata.objects.filter(Q(user=user) | Q(user__isnull=True))

        # 2. Get current month range
        now = timezone.now()
        
        for rule in rules:
            # Calculate total spent in the specific category this month
            category_total = Transaction.objects.filter(
                user=user,
                category=rule.trigger_category,
                timestamp__month=now.month,
                timestamp__year=now.year
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            # Calculate the percentage of income spent on this category
            current_percentage = (category_total / income) 

            # 3. Check threshold breach
            if current_percentage > rule.threshold_percentage:
                triggers.append(f"{rule.rule_name.upper()}_BREACHED")
        
        # 4. Supplemental Logic: Emergency Fund Check
        # If savings goal is set but current month expenses > 90% of income
        total_monthly_expenses = Transaction.objects.filter(
            user=user,
            timestamp__month=now.month,
            timestamp__year=now.year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        if total_monthly_expenses > (income * Decimal('0.90')):
            triggers.append("LOW_SURPLUS_RISK")

        # 5. Check for "Zero-Balance" savings events
        # (Logic: If user has a 'Savings' category but total is 0)
        # This triggers a "Right or Wrong" nudge to encourage the user.
        
    except Profile.DoesNotExist:
        pass
        
    return triggers