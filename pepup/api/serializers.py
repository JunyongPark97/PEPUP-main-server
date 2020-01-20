from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.http import Http404
from django.conf import settings
from .models import (Product, Brand, Payment,
                     Trade, Category, ProdThumbnail,
                     Like, Follow, Deal)
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
    product = ProductSerializer(read_only=True)
    seller = UserSerializer()
    buyer = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Trade
        fields = ('id','product', 'seller', 'buyer')


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


class ItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='name')
    unique = serializers.CharField(source='pk')
    price = serializers.SerializerMethodField('get_discount_price')
    qty = serializers.IntegerField(default=1)

    class Meta:
        model = Product
        fields = ('item_name','unique', 'price','qty')

    def get_discount_price(self, obj):
        return obj.price * (1-obj.discount_rate)


class UserinfoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='nickname')
    addr = serializers.CharField(default='')

    class Meta:
        model = User
        fields = ('username', 'addr', 'email', 'phone')


class PayFormSerializer(serializers.Serializer):
    price = serializers.IntegerField()
    application_id = serializers.CharField(default="5e05af1302f57e00219c40da")
    name = serializers.SerializerMethodField()
    pg = serializers.CharField(default='inicis')
    method = serializers.CharField(default='')
    items = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()
    order_id = serializers.CharField(default='1')

    def get_name(self,obj):
        return self.context.get('name')

    def get_items(self,obj):
        items = self.context.get('products')
        return ItemSerializer(items, many=True).data

    def get_user_info(self,obj):
        user_info = self.context.get('user')
        return UserinfoSerializer(user_info).data


class DealSerializer(serializers.ModelSerializer):
    seller = serializers.PrimaryKeyRelatedField(read_only=True)
    trades = serializers.SerializerMethodField()
    total = serializers.IntegerField()
    delivery_charge = serializers.IntegerField()

    class Meta:
        model = Deal
        fields = ['seller', 'trades', 'totol', 'delivery_charge']

    def get_trades(self, obj):
        trades = obj.trade_set.all()
        return trades
