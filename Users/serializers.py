from rest_framework import serializers  # <--- This is the missing line!
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    # Mapping phone_no from frontend to phone_number in backend
    f_name = serializers.CharField(write_only=True, required=True)
    l_name = serializers.CharField(write_only=True, required=True)
    phone_no = serializers.CharField(source='phone_number', required=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_no', 'password', 'f_name', 'l_name']

    def create(self, validated_data):
        # Extract profile-specific identity data
        f_name = validated_data.pop('f_name', '')
        l_name = validated_data.pop('l_name', '')
        phone_number = validated_data.get('phone_number')

        # Create user with hashed password
        user = User.objects.create_user(
            first_name=f_name,
            last_name=l_name,
            **validated_data
        )
        
        # Automatically create the linked Profile
        Profile.objects.create(
            user=user,
            f_name=f_name,
            l_name=l_name,
            phone_number=phone_number
        )
        return user

class ProfileSerializer(serializers.ModelSerializer):
    # Mapping custom keys for the frontend
    _id = serializers.IntegerField(source='id', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    # Nested groupings to match the frontend expectations
    demographic = serializers.SerializerMethodField()
    financial_context = serializers.SerializerMethodField()
    behavioural_context = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            '_id', 'user_id', 'f_name', 'l_name', 'phone_number',
            'demographic', 'financial_context', 'behavioural_context'
        ]

    def get_demographic(self, obj):
        return {
            "age": obj.age,
            "occupation": obj.occupation,
            "location": getattr(obj, 'location', 'Nairobi')
        }

    def get_financial_context(self, obj):
        return {
            "monthly_income": float(obj.monthly_income),
            "savings_target": float(getattr(obj, 'savings_target', 0.00))
        }

    def get_behavioural_context(self, obj):
        return {
            "risk_appetite": obj.risk_appetite,
            "financial_goal": obj.financial_goal
        }