from rest_framework import serializers
from .models import FinancialGoal, Transaction, Category

#new serializers
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon_name', 'color_code', 'is_essential']

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
