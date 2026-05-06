from django.urls import path
from .views import ConversationListCreateView, MessageCreateView, ConversationDetailView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='conversations'),
    path('conversations/<pk>/', ConversationDetailView.as_view(), name='conversation_detail'),
    path('messages/', MessageCreateView.as_view(), name='send_message'),
]