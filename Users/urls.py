from django.urls import path
from .views import UserSignupView, ProfileUpdateView, AccountDeleteView,UserLoginView

urlpatterns = [
    # Auth
    path('auth/signup/', UserSignupView.as_view(), name='user_signup'),
   path('auth/login/', UserLoginView.as_view(), name='user_login'),
    path('auth/delete/', AccountDeleteView.as_view(), name='account_delete'),
    
    # Profile
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
]