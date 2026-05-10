from django.urls import path
from .views import ConversationListCreateView, MessageCreateView, ConversationDetailView , NudgeListView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='conversations'),
    path('conversations/<pk>/', ConversationDetailView.as_view(), name='conversation_detail'),
    path('messages/', MessageCreateView.as_view(), name='send_message'),
    # Nudges.
    path('nudges/', NudgeListView.as_view(), name='nudge_list'),
    path('nudges/<uuid:pk>/', NudgeListView.as_view(), name='nudge_dismiss'),

]