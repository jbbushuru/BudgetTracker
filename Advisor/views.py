from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from .models import Conversation, ChatMessage
from .serializers import ConversationSerializer, ChatMessageSerializer
from .services import AdvisorService
from Finance.models import Transaction 
import logging

class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
       
        conversations = Conversation.objects.filter(user=request.user)
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)

    def post(self, request):
        
        title = request.data.get('title', 'New Chat')
        conversation = Conversation.objects.create(user=request.user, title=title)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conv_id = request.data.get('conversation_id')
        content = request.data.get('content')
        
        try:
            conversation = Conversation.objects.get(id=conv_id, user=request.user)
        except (Conversation.DoesNotExist, ValueError):
            return Response({"error": "Conversation not found"}, status=404)

        # 1. Save User Message
        user_msg = ChatMessage.objects.create(conversation=conversation, role='user', content=content)

        # 2. Build Context
        profile = request.user.profile # This is the Profile model instance
        
        spending_stats = Transaction.objects.filter(
            user=request.user, 
            transaction_type='OUT'
        ).values('category__name').annotate(total=Sum('amount'))
        
        snapshot = {stat['category__name'] or "Uncategorized": float(stat['total']) for stat in spending_stats}
        snapshot['total_income'] = float(profile.monthly_income)
        
        # Get history as model instances
        history = ChatMessage.objects.filter(conversation=conversation).order_by('-timestamp')[:5]

        # 3. Call Advisor Service with the model object
        advisor = AdvisorService()
        ai_response_data = advisor.get_advisor_response(
            user_query=content,
            profile=profile,  # <--- Passing the model object
            spending_snapshot=snapshot,
            triggers=[], 
            history=list(reversed(history))
        )

        # 4. Save AI Response
        ai_msg = ChatMessage.objects.create(
            conversation=conversation,
            role='ai',
            content=ai_response_data.ai_message
        )

        conversation.save() 
        
        return Response({
            "user_msg": ChatMessageSerializer(user_msg).data,
            "ai_msg": ChatMessageSerializer(ai_msg).data
        }, status=status.HTTP_201_CREATED)

class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            conversation = Conversation.objects.get(id=pk, user=request.user)
            conversation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)