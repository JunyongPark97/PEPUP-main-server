from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.http import Http404

from .models import (Product, Brand, Payment,
                     Trade, Category, ProdThumbnail,
                     Like, Follow)
from accounts.models import User

from accounts.serializers import UserSerializer


class PaymentSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)

    def get_user(self, token):
        try:
            user = Token.objects.get(key=token).user
            return user
        except:
            raise Http404

    class Meta:
        model = Payment
        fields = '__all__'


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['user','product','is_liked']


class ProdThumbnailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdThumbnail
        fields = ['thumbnail',]


class ProductSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    seller = UserSerializer()
    thumbnails = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.all()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails,many=True).data
        return [{"thumbnail":"http://1567e764.ngrok.io/media/%EC%86%90%EC%A4%80%ED%98%81%20/profile/%E1%84%8C%E1%85%A9%E1%84%8C%E1%85%A6_%E1%84%92%E1%85%A9%E1%84%85%E1%85%A1%E1%86%BC%E1%84%8B%E1%85%B5_%E1%84%80%E1%85%B3%E1%84%85%E1%85%B5%E1%84%80%E1%85%A9_%E1%84%86%E1%85%AE%E1%86%AF%E1%84%80%E1%85%A9%E1%84%80%E1%85%B5%E1%84%83%E1%85%B3%E1%86%AF.jpg"}]



class MainSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    seller = UserSerializer()

    class Meta:
        model = Product
        fields = ['id', 'seller', 'on_discount', 'sold', 'is_refundable', 'thumbnails']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.all()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails,many=True).data
        return [{"thumbnail":"http://1567e764.ngrok.io/media/%EC%86%90%EC%A4%80%ED%98%81%20/profile/%E1%84%8C%E1%85%A9%E1%84%8C%E1%85%A6_%E1%84%92%E1%85%A9%E1%84%85%E1%85%A1%E1%86%BC%E1%84%8B%E1%85%B5_%E1%84%80%E1%85%B3%E1%84%85%E1%85%B5%E1%84%80%E1%85%A9_%E1%84%86%E1%85%AE%E1%86%AF%E1%84%80%E1%85%A9%E1%84%80%E1%85%B5%E1%84%83%E1%85%B3%E1%86%AF.jpg"}]


class TradeSerializer(serializers.ModelSerializer):
    choices = [
        (0, '결제전'),
        (1, '결제중'),
        (2, '결제완료'),
        (3, '배송중'),
        (4, '배송완료'),
        (5, '거래완료'),
        (-1, '결제취소'),
        (-2, '환불'),
    ]
    product = ProductSerializer(read_only=True)
    seller = UserSerializer()
    buyer = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Trade
        fields = ('id','product', 'seller', 'buyer')

class CategorySerializer(serializers.Serializer):
    pass


class FilterSerializer(serializers.Serializer):
    category = serializers.CharField(allow_blank=True, allow_null=True)
    size = serializers.CharField(allow_blank=True, allow_null=True)
    min_price = serializers.IntegerField(default=0)
    max_price = serializers.IntegerField(default=99999999999)
    brand = serializers.CharField(allow_blank=True, allow_null=True)
    color = serializers.CharField(allow_blank=True, allow_null=True)
    on_sale = serializers.BooleanField(default=False)


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = '__all__'