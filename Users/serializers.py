from rest_framework import serializers  # <--- This is the missing line!
from django.contrib.auth import get_user_model
from .models import Profile
import json

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
    
    # added validation checks for existing users to return descriptive error messages for duplicate entries.
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_phone_no(self, value):
        if User.objects.filter(phone_number=value).exists() or Profile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

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
    active_recommendation = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            '_id', 'user_id', 'f_name', 'l_name', 'phone_number',
            # switched to each field instead of the nested groupings, I however did not delete the nested groupings
            'age', 'occupation', 'location', 'monthly_income', 
            'savings_target', 'budget', 'fixed_costs', 'existing_savings',
            'financial_goal', 'risk_appetite', 'spending_temperament',
            'demographic', 'financial_context', 'behavioural_context',
            # AI recommendation: nested to match the frontend Profile interface
            'active_recommendation',
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
            "savings_target": float(getattr(obj, 'savings_target', 0.00)),
            # added some more fields in financial context. Idk what difference this made.
            "budget": float(getattr(obj, 'budget', 0.00)),
            "fixed_costs": float(getattr(obj, 'fixed_costs', 0.00)),
            "existing_savings": float(getattr(obj, 'existing_savings', 0.00))
        }

    def get_behavioural_context(self, obj):
        return {
            "risk_appetite": obj.risk_appetite,
            "financial_goal": obj.financial_goal
        }

    def get_active_recommendation(self, obj):
        """
        Unpacks the JSON blob stored in personalized_hook back into the
        active_recommendation structure the frontend Profile interface expects.
        Returns None if no recommendation has been generated yet.
        """
        if not obj.personalized_hook:
            return None
        try:
            data = json.loads(obj.personalized_hook)
            # Only treat it as a recommendation blob if it has a personalized_hook key
            if 'personalized_hook' not in data:
                return None
            return {
                "title": data.get('title', 'Featured Recommendation'),
                "icon": data.get('icon', 'star'),
                "personalized_hook": data.get('personalized_hook', ''),
                "action_text": data.get('action_text', ''),
                "expires_at": int(obj.recommendation_expires_at.timestamp()) if obj.recommendation_expires_at else None,
            }
        except (json.JSONDecodeError, AttributeError):
            return None