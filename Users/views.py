from dataclasses import asdict # Built-in, no install needed
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework import serializers
from django.contrib.auth import authenticate

from .models import Profile
from .serializers import SignupSerializer, ProfileSerializer
from Advisor.services import AdvisorService # Ensure this matches your folder/file

class UserSignupView(APIView):
    """
    CREATE: Handles /auth/signup/
    Registers a new user; Profile is created automatically by the Serializer.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User created successfully",
                "user_id": user.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileUpdateView(APIView):
    """
    GET: Retrieves the profile and triggers AI recommendation updates.
    PATCH: Updates specific profile fields (Monthly Income, Goals, etc.).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Directly access the profile (created during signup)
        profile = request.user.profile
        
        # 2. Layer 4: Intelligence Update
        # The AI doesn't 'create' the profile; it only populates the recommendation fields
        if profile.is_recommendation_at_stale():
            # Call your service to get fresh advice for the frontend
            advisor = AdvisorService()
            # This method should handle the Gemini logic to update profile fields
            advisor.generate_personalized_recommendation(profile) 
            profile.refresh_from_db()

        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        """
        Partial update for settings or onboarding changes.
        """
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AccountDeleteView(APIView):
    """
    DELETE: Removes the user and the associated profile via database cascade.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({
            "message": "Account and associated profile deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)

class CustomAuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        login_identifier = username or email or phone_number

        if login_identifier and password:
            user = authenticate(request=self.context.get('request'),
                                username=login_identifier, password=password)

            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "username", "email" or "phone_number" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

class CustomAuthToken(ObtainAuthToken):
    serializer_class = CustomAuthTokenSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'phone_number': getattr(user, 'phone_number', None)
        })