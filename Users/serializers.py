from rest_framework import serializers  # <--- This is the missing line!
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    f_name = serializers.CharField(write_only=True, required=True)
    l_name = serializers.CharField(write_only=True, required=True)
    phone_no = serializers.CharField(source='phone_number', required=True)
    password = serializers.CharField(write_only=True)
    # Username is now explicitly required from the frontend
    username = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_no', 'password', 'f_name', 'l_name']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_no(self, value):
        if User.objects.filter(phone_number=value).exists() or Profile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        f_name = validated_data.pop('f_name', '')
        l_name = validated_data.pop('l_name', '')
        phone_number = validated_data.get('phone_number')
        username = validated_data.get('username')

        # Create user with the provided username
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
            # switched to each field instead of the nested groupings, I however did not delete the nested groupings
            'age', 'occupation', 'location', 'monthly_income', 
            'savings_target', 'budget', 'fixed_costs', 'existing_savings',
            'financial_goal', 'risk_appetite', 'spending_temperament',
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