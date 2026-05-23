from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        login_identifier = username or kwargs.get('email') or kwargs.get('phone_number')
        
        if not login_identifier:
            return None

        try:
            user = UserModel.objects.get(
                Q(username=login_identifier) | 
                Q(email=login_identifier) | 
                Q(phone_number=login_identifier)
            )
        except UserModel.DoesNotExist:
            return None
            
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
