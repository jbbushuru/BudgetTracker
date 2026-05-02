from django.urls import path
from .views import ConversationListCreateView, MessageCreateView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='conversations'),
    path('messages/', MessageCreateView.as_view(), name='send_message'),
]