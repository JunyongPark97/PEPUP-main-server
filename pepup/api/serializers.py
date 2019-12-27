from rest_framework import serializers
from .models import Product
from accounts.models import User


class ProductSerializer(serializers.ModelSerializer):


    class Meta:
        model = Product
        fields = '__all__'
        depth = 1


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email','password']
        extra_kwargs = {'password': {'write_only':True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
