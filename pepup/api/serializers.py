from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.http import Http404
from django.conf import settings
from .models import (Product, Brand, Payment,
                     Trade, ProdThumbnail,
                     Like, Follow, Deal, Tag, SecondCategory)
from accounts.models import User, DeliveryPolicy

from accounts.serializers import UserSerializer,ThumbnailSerializer


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['is_liked']


class ProdThumbnailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdThumbnail
        fields = ['thumbnail',]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag', 'id']


class DeliveryPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPolicy
        fields = ['general', 'mountain', 'amount', 'volume']


class SecondCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecondCategory
        fields = ['name', 'id']


class RelatedProductSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'thumbnails', 'size', 'price', 'name']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.select_related('product').all()
        if not thumbnails:
            return [{"thumbnail": "https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdThumbnailSerializer(thumbnails, many=True).data

    def get_size(self, obj):
        if hasattr(obj.size, 'size_name'):
            return "{}".format(obj.size.size_name)
        else:
            return ""


class ProductSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    seller = UserSerializer()
    discounted_price = serializers.SerializerMethodField()
    thumbnails = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    second_category = SecondCategorySerializer(allow_null=True)
    tag = TagSerializer(many=True)

    class Meta:
        model = Product
        fields = '__all__'

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.select_related('product').all()
        if not thumbnails:
            return [{"thumbnail": "https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdThumbnailSerializer(thumbnails, many=True).data

    def get_size(self, obj):
        if obj.size.size_max:
            return "{}({}-{})".format(obj.size.size_name, obj.size.size, obj.size.size_max)
        if obj.size.category.name == 'SHOES':
            return "{}(cm)".format(obj.size.size)
        return "{}({})".format(obj.size.size_name, obj.size.size)

    def get_discounted_price(self,obj):
        return obj.discounted_price


class FollowSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    seller = UserSerializer()
    thumbnails = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    tag = serializers.StringRelatedField(many=True)
    by = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.select_related('product').all()
        if not thumbnails:
            return [{"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdThumbnailSerializer(thumbnails, many=True).data

    def get_by(self, obj):
        print(self.context)
        if obj.id in self.context.get('by_seller'):
            return 1
        return 2

    def get_discount_price(self, obj):
        discount_percent = obj.discount_rate
        discount_rate = 1 - discount_percent * 0.01
        discount_price = int(obj.price * discount_rate)
        return discount_price

    def get_liked(self, obj):
        request = self.context['request']
        user = request.user
        try:
            liked = obj.like_set.get(user=user).is_liked
            return liked
        except:
            return False


class MainSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    seller = UserSerializer()

    class Meta:
        model = Product
        fields = ['id', 'seller', 'on_discount', 'sold', 'is_refundable', 'thumbnails']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.all()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails, many=True).data
        return [{"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]


class SellerForTradeSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    def get_profile(self, obj):
        try:
            return ThumbnailSerializer(obj.profile).data
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
        thumbnails = obj.prodthumbnail_set.all()
        if not thumbnails:
            return [{"thumbnail": "https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdThumbnailSerializer(thumbnails, many=True).data

    def get_size(self, obj):
        if obj.size.size_max:
            return "{}({}-{})".format(obj.size.size_name, obj.size.size, obj.size.size_max)
        if obj.size.category.name == 'SHOES':
            return "{}(cm)".format(obj.size.size)
        return "{}({})".format(obj.size.size_name, obj.size.size)

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


class FilterSerializer(serializers.Serializer):
    category = serializers.CharField(allow_blank=True, allow_null=True)
    size = serializers.CharField(allow_blank=True, allow_null=True)
    min_price = serializers.IntegerField(default=0)
    max_price = serializers.IntegerField(default=99999999999)
    brand = serializers.CharField(allow_blank=True, allow_null=True)
    color = serializers.CharField(allow_blank=True, allow_null=True)
    on_sale = serializers.BooleanField(default=False)


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
    order_id = serializers.SerializerMethodField()

    def get_name(self,obj):
        return self.context.get('name')

    def get_items(self,obj):
        items = self.context.get('products')
        return ItemSerializer(items, many=True).data

    def get_user_info(self,obj):
        user_info = self.context.get('user')
        return UserinfoSerializer(user_info).data

    def get_order_id(self, obj):
        return {'order_id':self.context.get('order_id')}


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


class SearchResultSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'thumbnails', 'name', 'price',
                  'on_discount', 'discount_rate', 'discount_price', 'size',
                  'liked', 'is_refundable']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.all()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails, many=True).data
        return [{"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]

    def get_discount_price(self, obj):
        origin_price = obj.price
        discount_rate = obj.discount_rate
        discount_price = int(origin_price * (1 - discount_rate * 0.01))
        return discount_price

    def get_liked(self, obj):
        request = self.context['request']
        user = request.user
        try:
            liked = obj.like_set.get(user=user).is_liked
            return liked
        except:
            return False


class FollowingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = ['_to', 'tag', 'is_follow']