import datetime
import os
import urllib.request
import uuid

from django.conf import settings
from django.core.files import File
from django.http import Http404
from django.utils.timesince import timesince
from rest_framework import serializers
from django.db.models import Avg
from accounts.models import User, DeliveryPolicy, StoreAccount, Profile
from accounts.serializers import UserSerializer, ThumbnailSerializer
from payment.models import Review
from .models import (Product, Brand, ProdThumbnail,
                     Like, Follow, Tag, SecondCategory, FirstCategory, Size, GenderDivision, ProdImage,
                     ProdS3Image)
from api.loader import load_credential


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
        model = ProdS3Image
        fields = ['image_url',]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag', 'id']


class DeliveryPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPolicy
        fields = ['general', 'mountain', 'amount', 'volume']


class FirstCategorySerializer(serializers.ModelSerializer):
    child = serializers.SerializerMethodField()

    class Meta:
        model = FirstCategory
        fields = ['name', 'id', 'child']

    def get_child(self, obj):
        if obj.second_category.first():
            return True
        return False


class SecondCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecondCategory
        fields = ['name', 'id']


class GenderSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    child = serializers.SerializerMethodField()

    class Meta:
        model = GenderDivision
        fields = ['name', 'id', 'child']

    def get_name(self, obj):
        return obj.get_name_display()

    def get_child(self, obj):
        if obj.category.first():
            return True
        return False


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
        thumbnails = obj.prodthumbnail
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
        image_keys = product_data.pop('image_keys', [])

        product = self.Meta.model.objects.create(**product_data)

        # Images
        for image_key in image_keys:
            data = {}
            data.update({'product': product})
            data.update({'image_key': image_key})
            ProdS3Image.objects.create(**data)

        # Thumbnail 은 Product당 하나 생성됨.
        thumb_data = {'product': product}
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
    age = serializers.SerializerMethodField()
    follow_tag = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_images(self, obj):
        images = obj.images.select_related('product').all()
        if not images:
            return [{"image":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}]
        return ProdImageSerializer(images, many=True).data

    def get_by(self, obj):
        if obj.id in self.context['by_seller']:
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

    def get_follow_tag(self, obj):
        follow_tag_ids = self.context['follow_tag_ids']
        tags = obj.tag.all()
        for tag in tags:
            if tag.id in follow_tag_ids:
                return TagSerializer(tag).data
        return None



    def get_age(self, obj):
        now = datetime.datetime.now()
        created_at = obj.created_at
        try:
            diff = now - created_at
        except:
            return created_at

        if diff <= datetime.timedelta(minutes=1):
            return 'just now'
        return '%(time)s ago' % {'time': timesince(created_at).split(', ')[0]}


class MainSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    # seller = UserSerializer()

    class Meta:
        model = Product
        fields = ['id', 'on_discount', 'sold', 'is_refundable', 'thumbnails']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails).data
        return {"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}


class FilterSerializer(serializers.Serializer):
    category = serializers.CharField(allow_blank=True, allow_null=True)
    size = serializers.CharField(allow_blank=True, allow_null=True)
    min_price = serializers.IntegerField(default=0)
    max_price = serializers.IntegerField(default=99999999999)
    brand = serializers.CharField(allow_blank=True, allow_null=True)
    color = serializers.CharField(allow_blank=True, allow_null=True)
    on_sale = serializers.BooleanField(default=False)


class UserinfoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='nickname')
    addr = serializers.CharField(default='')

    class Meta:
        model = User
        fields = ('username', 'addr', 'email', 'phone')


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
        thumbnails = obj.prodthumbnail
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


class StoreProductSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['thumbnails', 'id']

    def get_thumbnails(self, obj):
        thumbnails = obj.prodthumbnail
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails).data
        return {"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}


class StoreSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    profile_introduce = serializers.SerializerMethodField()
    review_score = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    followers = serializers.SerializerMethodField()
    followings = serializers.SerializerMethodField()
    user_followed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'nickname', 'profile', 'profile_introduce', 'review_score',
                  'review_count', 'followers', 'followings', 'user_followed']

    def get_profile(self, obj):
        return obj.profile.profile_img_url

    def get_profile_introduce(self, obj):
        if hasattr(obj, 'profile'):
            profile = obj.profile
            if profile.introduce:
                return profile.introduce
        return ''

    def get_review_score(self, obj):
        if obj.received_reviews.first():
            score = obj.received_reviews.all().values('satisfaction').annotate(score=Avg('satisfaction')).values('score')[0]['score']
            return score
        return 0.0

    def get_review_count(self, obj):
        if obj.received_reviews.first():
            count = obj.received_reviews.all().count()
            return count
        return 0

    def get_followers(self, obj):
        follower = Follow.objects.filter(_to=obj, is_follow=True)
        return follower.count()

    def get_followings(self, obj):
        following = Follow.objects.filter(_from=obj, is_follow=True, tag__isnull=True)
        return following.count()

    def get_user_followed(self, obj):
        user_followed = self.context['user_followed']
        return user_followed


class StoreLikeSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    sold = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = ['thumbnails', 'id', 'sold']

    def get_thumbnails(self, obj):
        thumbnails = obj.product.prodthumbnail
        if thumbnails:
            return ProdThumbnailSerializer(thumbnails).data
        return {"thumbnail":"https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/static/img/prodthumbnail_default.png"}

    def get_id(self, obj):
        if obj.product:
            return obj.product.id
        return None

    def get_sold(self, obj):
        if obj.product:
            return obj.product.sold
        return False


class SimpleProfileSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    review_score = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'profile', 'review_score', 'nickname']

    def get_profile(self, obj):
        return obj.profile.profile_img_url

    def get_review_score(self, obj):
        if obj.received_reviews.first():
            score = obj.received_reviews.all().values('satisfaction').\
                annotate(score=Avg('satisfaction')).values('score')[0]['score']
            return score
        return 0


class StoreReviewSerializer(serializers.ModelSerializer):
    buyer_profile = serializers.SerializerMethodField()
    buyer_name = serializers.SerializerMethodField()
    satisfaction = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['buyer_name','buyer_profile', 'context', 'satisfaction', 'thumbnail', 'created_at']

    def get_buyer_profile(self, obj):
        buyer = obj.buyer
        return buyer.profile.profile_img_url

    def get_buyer_name(self, obj):
        buyer = obj.buyer
        nickname = buyer.nickname
        return nickname

    def get_satisfaction(self, obj):
        satisfaction = obj.satisfaction
        return float(satisfaction)


class StoreProfileRetrieveSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    introduce = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['profile', 'nickname', 'introduce']

    def get_profile(self, obj):
        profile = obj.profile
        return profile.profile_img_url

    def get_introduce(self, obj):
        profile = obj.profile
        return profile.introduce


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


class DeliveryPolicyWriteSerializer(serializers.ModelSerializer):
    seller = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = DeliveryPolicy
        fields = '__all__'

    def create(self, validated_data):
        request = self.context['request']

        # Product
        delivery_data = validated_data
        account_data = delivery_data.pop('account_data', None)
        account_data.update({'user': request.user})
        delivery_policy = self.Meta.model.objects.create(**delivery_data)

        # store account
        StoreAccount.objects.get_or_create(**account_data)

        # Done!
        return delivery_policy


class StoreAccountSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    bank = serializers.SerializerMethodField()
    bank_id = serializers.SerializerMethodField()

    class Meta:
        model = StoreAccount
        fields = ['user', 'bank', 'bank_id', 'account', 'account_holder']

    def get_bank(self, obj):
        return obj.get_bank_display()

    def get_bank_id(self, obj):
        bank = obj.bank
        return bank


class StoreAccountWriteSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = StoreAccount
        fields = ['user', 'bank', 'account', 'account_holder']
