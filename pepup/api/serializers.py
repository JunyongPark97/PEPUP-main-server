from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.http import Http404

from .models import Product, Brand, Payment
from accounts.models import User



class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)

    def get_user(self, token):
        try:
            user = Token.objects.get(key=token).user
            return user
        except:
            raise Http404

    class meta:
        model = Payment
        fields = '__all__'


class BrandSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)

    class meta:
        model = Brand
        fields = '__all__'