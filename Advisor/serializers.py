from rest_framework import serializers
from .models import Conversation, ChatMessage

class ConversationSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id')
    user_id = serializers.CharField(source='user.id')

    class Meta:
        model = Conversation
        fields = ['_id', 'user_id', 'title', 'created_at', 'updated_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id')
    conversation_id = serializers.CharField(source='conversation.id')

    class Meta:
        model = ChatMessage
        fields = ['_id', 'conversation_id', 'role', 'content', 'category_referenced', 'timestamp']