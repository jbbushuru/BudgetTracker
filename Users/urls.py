from django.urls import path
from .views import UserSignupView, ProfileUpdateView, AccountDeleteView, CustomAuthToken

urlpatterns = [
    # Auth
    path('auth/signup/', UserSignupView.as_view(), name='user_signup'),
    path('auth/login/', CustomAuthToken.as_view(), name='user_login'), # Custom login with email/phone/username
    path('auth/delete/', AccountDeleteView.as_view(), name='account_delete'),
    
    # Profile
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
]