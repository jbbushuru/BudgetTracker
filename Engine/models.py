# engine/models.py
from django.db import models
from django.conf import settings
from Finance.models import Category

class RuleMetadata(models.Model):
    SEVERITY_CHOICES = [('WARNING', 'Warning'), ('CRITICAL', 'Critical'), ('POSITIVE', 'Positive')]
    
    rule_name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True) # Null = Global
    trigger_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    threshold_percentage = models.DecimalField(max_digits=5, decimal_places=2) # e.g., 0.30 for 30%
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)