import uuid
from django.db import models
from django.conf import settings

class Conversation(models.Model):
    """
    Represents a unique chat thread. 
    UUIDs are used to match the 'conv_generated_uuid' format for the mobile frontend.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class ChatMessage(models.Model):
    """
    Individual messages within a conversation.
    Supports user queries, AI responses, and system nudges.
    """
    ROLE_CHOICES = [('user', 'User'), ('ai', 'AI'), ('nudge', 'Nudge')]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # FIX: Added null=True, blank=True to bypass the 'non-nullable' migration error
    conversation = models.ForeignKey(
        Conversation, 
        related_name='messages', 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES , default='user')
    content = models.TextField()
    
    # Link to a finance category (e.g., 'cat_food') for UI highlighting
    category_referenced = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

class KnowledgeBase(models.Model):
    """
    Static financial facts and local USSD codes for Finn to reference.
    """
    TYPE_CHOICES = [('SAVING', 'Saving'), ('INVESTMENT', 'Investment'), ('LOAN', 'Loan')]
    
    title = models.CharField(max_length=100)
    instrument_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    key_fact = models.TextField() 
    local_context = models.TextField() # e.g., "Accessible via *889#"
    last_updated = models.DateTimeField(auto_now=True)

class AdvisoryLog(models.Model):
    """
    Research-focused log to track how triggers (e.g., overspending) 
    resulted in specific AI responses.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    trigger_event = models.CharField(max_length=255) 
    ai_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class Nudge(models.Model):
    # Distinct entity from ChatMessage
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Nudge content
    type = models.CharField(max_length=20, default="WARNING") # e.g., WARNING, INSIGHT, SUCCESS
    message = models.TextField() # Short, punchy phrase
    impact_on_goal = models.CharField(max_length=255) # Reference to the Ruai goal
    suggested_action = models.CharField(max_length=255) # Actionable advice
    
    # Metadata
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']