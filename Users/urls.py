from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import UserSignupView, ProfileUpdateView, AccountDeleteView

urlpatterns = [
    # Auth
    path('auth/signup/', UserSignupView.as_view(), name='user_signup'),
    path('auth/login/', obtain_auth_token, name='user_login'), # Added for Postman testing
    path('auth/delete/', AccountDeleteView.as_view(), name='account_delete'),
    
    # Profile
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
]