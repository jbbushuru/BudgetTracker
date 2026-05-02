# finance/models.py
from django.db import models
from django.conf import settings

class Category(models.Model):
    _id=  models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True) # Null = System Default
    icon_name = models.CharField(max_length=30, default='category')
    is_essential = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Categories"

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('IN', 'Received'),
        ('OUT', 'Sent'),
    ]
    SOURCE_CHOICES = [('MPESA', 'M-Pesa SMS'), ('CASH', 'Manual Cash'),('BANK','Bank')]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='MPESA')
    transaction_type = models.CharField(
        max_length=3, 
        choices=TRANSACTION_TYPE_CHOICES, 
        default='OUT'
    )
    sms_batch= models.TextField(null=True, blank=True) # Stores the original SMS string
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    recipient = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_pending_categorization = models.BooleanField(default=True) # For the pop-up logic