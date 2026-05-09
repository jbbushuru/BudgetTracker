from rest_framework import serializers
from .models import FinancialGoal, Transaction, Category

#new serializers
class CategorySerializer(serializers.ModelSerializer):
    # True if the category was created by a user (owner != None).
    # The frontend uses this flag to conditionally show edit/delete buttons.
    is_user_created = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'icon_name', 'color_code', 'is_essential', 'is_user_created']
        # owner is set server-side; never accepted from the client
        read_only_fields = ['id', 'is_user_created']

    def get_is_user_created(self, obj):
        return obj.owner is not None

class TransactionSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'fee', 'recipient', 'transaction_type', 
            'source', 'category', 'timestamp', 'is_pending_categorization'
        ]


# I created a new serializer to handle the conversion between Python objects and the JSON format my React Native app expects.
# It includes:
# name, description, target_amount, amount_saved, deadline, is_completed.
# read_only_fields for id and user.
# A create method to automatically set the user.
class FinancialGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialGoal
        fields = [
            'id', 'name', 'description', 'target_amount', 
            'amount_saved', 'deadline', 'is_completed'
        ]
        read_only_fields = ['id', 'user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
