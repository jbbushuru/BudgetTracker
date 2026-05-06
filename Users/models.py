from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    # fcm_token = models.TextField(null=True, blank=True)

class Profile(models.Model):
    RISK_CHOICES = [('Conservative', 'Conservative'), ('Moderate', 'Moderate'), ('Aggressive', 'Aggressive')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    f_name = models.CharField(max_length=50, blank=True)
    l_name = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    age = models.IntegerField(null=True)
    occupation = models.CharField(max_length=100)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    financial_goal = models.CharField(max_length=255)
    risk_appetite = models.CharField(max_length=20, choices=RISK_CHOICES, default='Moderate')
    category_overrides = models.JSONField(default=dict, blank=True) 
    recommendation_last_updated = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=100, default="Nairobi")
    fixed_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    existing_savings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    savings_target = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    #added the budget field
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    spending_temperament = models.CharField(max_length=50, blank=True)
    
    # AI Recommendation fields
    kb_item = models.ForeignKey('Advisor.KnowledgeBase', on_delete=models.SET_NULL, null=True, blank=True)
    personalized_hook = models.TextField(blank=True)
    action_text = models.CharField(max_length=255, blank=True)
    recommendation_expires_at = models.DateTimeField(null=True, blank=True)
    push_token = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    def is_recommendation_at_stale(self):
        # Example: Advice is stale after 24 hours
        return timezone.now() > self.recommendation_last_updated + timedelta(hours=24)