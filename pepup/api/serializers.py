from django.conf import settings
from django.http import Http404
from rest_framework import serializers
from django.db.models import Avg
from accounts.models import User, DeliveryPolicy
from accounts.serializers import UserSerializer, ThumbnailSerializer
from .models import (Product, Brand, Trade, ProdThumbnail,
                     Like, Follow, Deal, Tag, SecondCategory, FirstCategory, Size, GenderDivision, ProdImage, Review)


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


class ProdImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdImage
        fields = ['image',]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag', 'id']


class DeliveryPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPolicy
        fields = ['general', 'mountain', 'amount', 'volume']


class FirstCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FirstCategory
        fields = ['name', 'id']


class SecondCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecondCategory
        fields = ['name', 'id']


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenderDivision
        fields = ['name', 'id']


class SizeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Size
        fields = ['id', 'name']

    def get_name(self, obj):
        if obj.size_max:
            return "{} ({}-{})".format(obj.size_name, obj.size, obj.size_max)
        return "{} ({})".format(obj.size_name, obj.size)


class RelatedProductSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'thumbnails', 'size', 'price', 'name']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.first()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails).data
        return {"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}

    def get_size(self, obj):
        if hasattr(obj.size, 'size_name'):
            return "{}".format(obj.size.size_name)
        else:
            return None


class ProductSerializer(serializers.ModelSerializer):
    """
    Detail page 에서만 사용하는 serializer
    """
    brand = BrandSerializer(read_only=True)
    seller = UserSerializer()
    discounted_price = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField() # TODO : FIX field name 'thumbnalis' -> 'images'
    size = serializers.SerializerMethodField()
    second_category = SecondCategorySerializer(allow_null=True)
    tag = TagSerializer(many=True)

    class Meta:
        model = Product
        fields = '__all__'

    def get_images(self, obj):
        images = obj.images.select_related('product').all()
        if not images:
            return [{"image": "https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdImageSerializer(images, many=True).data

    def get_size(self, obj):
        if not obj.size:
            return None
        if obj.size.size_max:
            return "{}({}-{})".format(obj.size.size_name, obj.size.size, obj.size.size_max)
        if obj.size.category.name == 'SHOES':
            return "{}(cm)".format(obj.size.size)
        return "{}({})".format(obj.size.size_name, obj.size.size)

    def get_discounted_price(self, obj):
        return obj.discounted_price


class ProductCreateSerializer(serializers.ModelSerializer):
    seller = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'price',
            'content',
            'first_category', 'second_category',
            'size',
            'brand',
            'seller'
        ]

    def create(self, validated_data):

        # Product
        product_data = validated_data
        image_data = product_data.pop('images', [])

        product = self.Meta.model.objects.create(**product_data)

        # Images
        for image in image_data:
            data = {}
            data.update({'product': product})
            data.update({'image': image})
            ProdImage.objects.create(**data)

        # Thumbnail 은 Product당 하나 생성됨.
        thumb_data = {'product': product, 'thumbnail': image_data[0]}
        ProdThumbnail.objects.create(**thumb_data)

        # Done!
        return product


class FollowSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    seller = UserSerializer()
    images = serializers.SerializerMethodField()
    tag = TagSerializer(many=True)
    by = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    second_category = SecondCategorySerializer(allow_null=True)
    size = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_images(self, obj):
        images = obj.images.select_related('product').all()
        if not images:
            return [{"image":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdImageSerializer(images, many=True).data

    def get_by(self, obj):
        if obj.id in self.context.get('by_seller'):
            return 1
        return 2

    def get_discounted_price(self,obj):
        return obj.discounted_price

    def get_liked(self, obj):
        request = self.context['request']
        user = request.user
        try:
            liked = obj.like_set.get(user=user).is_liked
            return liked
        except:
            return False

    def get_size(self, obj):
        if not obj.size:
            return None
        if obj.size.size_max:
            return "{}({}-{})".format(obj.size.size_name, obj.size.size, obj.size.size_max)
        if obj.size.category.name == 'SHOES':
            return "{}(cm)".format(obj.size.size)
        return "{}({})".format(obj.size.size_name, obj.size.size)


class MainSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    # seller = UserSerializer()

    class Meta:
        model = Product
        fields = ['id', 'on_discount', 'sold', 'is_refundable', 'thumbnails']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.first()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails).data
        return {"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}


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
        thumbnails = obj.prodthumbnail_set.first()
        if not thumbnails:
            return {"thumbnail": "https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}
        return ProdThumbnailSerializer(thumbnails).data

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

    def get_name(self, obj):
        return self.context.get('name')

    def get_items(self, obj):
        items = self.context.get('products')
        return ItemSerializer(items, many=True).data

    def get_user_info(self, obj):
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
    images = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'images', 'name', 'price',
                  'on_discount', 'discount_rate', 'discounted_price', 'size',
                  'liked', 'is_refundable', 'size']

    def get_images(self, obj):
        images = obj.images.select_related('product').first()
        if not images:
            return [{"image":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdImageSerializer(images).data

    def get_discounted_price(self,obj):
        return obj.discounted_price

    def get_liked(self, obj):
        request = self.context['request']
        user = request.user
        try:
            liked = obj.like_set.get(user=user).is_liked
            return liked
        except:
            return False

    def get_size(self, obj):
        if hasattr(obj.size, 'size_name'):
            return "{}".format(obj.size.size_name)
        else:
            return None


class FollowingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = ['_to', 'tag', 'is_follow']


class StoreProductSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['thumbnails', 'id']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.first()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails).data
        return {"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}


class StoreSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    profile_introduce = serializers.SerializerMethodField()
    review_score = serializers.SerializerMethodField()
    follower = serializers.SerializerMethodField()
    following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'nickname', 'profile', 'profile_introduce', 'review_score',
                  'follower', 'following']

    def get_profile(self, obj):
        try:
            profile = obj.profile
            return ThumbnailSerializer(profile).data
        except:
            return {"thumbnail_img": "{}img/profile_default.png".format(settings.STATIC_ROOT)}

    def get_profile_introduce(self, obj):
        profile = obj.profile
        if profile.introduce:
            return profile.introduce
        return ''

    def get_review_score(self, obj):
        if obj.received_reviews.first():
            score = obj.received_reviews.all().values('satisfaction').annotate(score=Avg('satisfaction')).values('score')[0]['score']
            return score
        return 0

    def get_follower(self, obj):
        follower = Follow.objects.filter(_to=obj, is_follow=True)
        return follower.count()

    def get_following(self, obj):
        following = Follow.objects.filter(_from=obj, is_follow=True, tag__isnull=True)
        return following.count()


class StoreLikeSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = ['thumbnails', 'id']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail_set.first()
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails).data
        return {"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}

    def get_id(self, obj):
        if obj.product:
            return obj.product.id
        return None


class SimpleProfileSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    review_score = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'profile', 'review_score', 'nickname']

    def get_profile(self, obj):
        try:
            profile = obj.profile
            return ThumbnailSerializer(profile).data
        except:
             return {"thumbnail_img": "{}img/profile_default.png".format(settings.STATIC_ROOT)}

    def get_review_score(self, obj):
        if obj.received_reviews.first():
            score = obj.received_reviews.all().values('satisfaction').\
                annotate(score=Avg('satisfaction')).values('score')[0]['score']
            return score
        return 0


class StoreReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['buyer', 'context', 'satisfaction', 'thumbnail', 'created_at']


class GetPayFormSerializer(serializers.Serializer):
    trades = serializers.ListField()
    price = serializers.IntegerField()
    address = serializers.CharField()
    memo = serializers.CharField()
    mountain = serializers.BooleanField()


class ReviewCreateSerializer(serializers.ModelSerializer):
    buyer = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Review
        fields = [
            'seller', 'buyer',
            'context',
            'satisfaction',
            'deal',
            'thumbnail'
        ]
