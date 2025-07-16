from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserAccounts, Stock, Expiry_Stock # your custom model

class UserInfoSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password')

    def create(self, validated_data):
        user = User(
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class ClientRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccounts
        fields = ['acc_name', 'acc_provider', 'app_key', 'secret_key']



class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__' 


class ExpiryStockSerializer(serializers.Serializer):
    class Meta:
        model = Expiry_Stock
        fields = '__all__'