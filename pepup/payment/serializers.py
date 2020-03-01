from django.conf import settings
from rest_framework import serializers
from accounts.models import User, DeliveryPolicy
from accounts.serializers import ThumbnailSerializer
from api.serializers import BrandSerializer, SecondCategorySerializer, ProdThumbnailSerializer
from .models import (Product, Trade, Deal, Payment)
from api.loader import load_credential


class SellerForTradeSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    def get_profile(self, obj):
        if hasattr(obj.socialaccount_set.last(), 'extra_data'):
            social_profile_img = obj.socialaccount_set.last().extra_data['properties'].get('profile_image')
            return {"thumbnail_img": social_profile_img}
        try:
            profile = obj.profile
            return ThumbnailSerializer(profile).data
        except:
            return {"thumbnail_img": "{}img/profile_default.png".format(settings.STATIC_ROOT)}

    class Meta:
        model = User
        fields = ['id', 'nickname', 'profile']


class ProductForTradeSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    thumbnails = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    second_category = SecondCategorySerializer(allow_null=True)
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id','name','price', 'discount_rate','discounted_price','brand', 'thumbnails', 'size', 'second_category']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.first()
        if not thumbnails:
            return {"thumbnail": "https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}
        return ProdThumbnailSerializer(thumbnails).data

    def get_size(self, obj):
        if hasattr(obj.size, 'size_max'):
            if obj.size.size_max:
                return "{}({}-{})".format(obj.size.size_name, obj.size.size, obj.size.size_max)
            if obj.size.category.name == 'SHOES':
                return "{}(cm)".format(obj.size.size)
        if hasattr(obj.size,'size_name'):
            return "{}({})".format(obj.size.size_name, obj.size.size)
        return ""

    def get_discounted_price(self,obj):
        return obj.discounted_price


class PaymentInfoForTrade(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPolicy
        fields = '__all__'


class TradeSerializer(serializers.ModelSerializer):
    product = ProductForTradeSerializer(read_only=True)
    seller = SellerForTradeSerializer()
    payinfo = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = ('id', 'product', 'seller', 'payinfo')

    def get_payinfo(self, obj):
        return PaymentInfoForTrade(obj.seller.delivery_policy).data


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


class GetPayFormSerializer(serializers.Serializer):
    trades = serializers.ListField()
    price = serializers.IntegerField()
    address = serializers.CharField()
    memo = serializers.CharField(allow_blank=True)
    mountain = serializers.BooleanField(default=False)
    application_id = serializers.IntegerField() # 1: web 2:android 3:ios


class ItemSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()
    unique = serializers.CharField(source='pk')
    price = serializers.IntegerField(source='total')
    qty = serializers.IntegerField(default=1)

    class Meta:
        model = Deal
        fields = ('item_name', 'unique', 'price', 'qty')

    def get_item_name(self, obj):
        return obj.seller.email


class PayformSerializer(serializers.ModelSerializer):
    application_id = serializers.SerializerMethodField()
    order_id = serializers.IntegerField(source='id')
    items = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()
    pg = serializers.CharField(default='inicis')
    method = serializers.CharField(default='')

    class Meta:
        model = Payment
        fields = ['price', 'application_id', 'name', 'pg', 'method', 'items', 'user_info', 'order_id']

    def get_items(self, obj):
        return ItemSerializer(obj.deal_set.all(), many=True).data

    def get_user_info(self, obj):
        return {
            'username': obj.user.nickname,
            'email': obj.user.email,
            'addr': self.context.get('addr'),
            'phone': obj.user.phone
        }

    def get_application_id(self,obj):
        if self.context.get('application_id') == '1':
            return load_credential('application_id_web')
        elif self.context.get('application_id') == '2':
            return load_credential('application_id_android')
        elif self.context.get('application_id') == '3':
            return load_credential('application_id_ios')
        else:
            return ""


class PaymentDoneSerialzier(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = [
            'remain_price', 'tax_free', 'remain_tax_free',
            'cancelled_price', 'cancelled_tax_free',
            'requested_at', 'purchased_at', 'status'
        ]


class PaymentCancelSerialzier(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'remain_price', 'remain_tax_free',
            'cancelled_price', 'cancelled_tax_free',
            'revoked_at', 'status'
        ]
