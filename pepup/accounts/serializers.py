from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate, get_user_model

from api.models import Product, Follow
from .models import User, PhoneConfirm, Profile
from .utils import SMSManager
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email","password", "nickname","phone")

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            nickname=validated_data['nickname'],
            phone=validated_data['phone']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class PhoneConfirmSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneConfirm
        fields = '__all__'

    # 세션완료, 5분
    def timeout(self, instance):
        if not instance.is_confirmed:
            if timezone.now().timestamp() - instance.created_at.timestamp() >= 300:
                instance.delete()
                return True
        return False


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def authenticate(self, **kwargs):
        return authenticate(self.context['request'], **kwargs)

    def _validate_email(self, email, password):
        user = None
        if email and password:
            user = self.authenticate(email=email, password=password)
        else:
            msg = _('Must include "email" and "password".')
            raise exceptions.ValidationError(msg)

        return user

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = self._validate_email(email, password)

        # Did we get back an active user?
        if user:
            if not user.is_active:
                msg = _('User account is disabled.')
                raise exceptions.ValidationError(msg)
        else:
            msg = _('Unable to log in with provided credentials.')
            raise exceptions.ValidationError(msg)

        attrs['user'] = user
        return attrs


class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ('key',)


class ThumbnailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['thumbnail_img']

    def get_thumbnail_img(self, obj):
        thumbnail_img = obj.thumbnail_img
        if thumbnail_img:
            return thumbnail_img.url
        return "http://1567e764.ngrok.io/media/%EC%86%90%EC%A4%80%ED%98%81%20/profile/%E1%84%8C%E1%85%A9%E1%84%8C%E1%85%A6_%E1%84%92%E1%85%A9%E1%84%85%E1%85%A1%E1%86%BC%E1%84%8B%E1%85%B5_%E1%84%80%E1%85%B3%E1%84%85%E1%85%B5%E1%84%80%E1%85%A9_%E1%84%86%E1%85%AE%E1%86%AF%E1%84%80%E1%85%A9%E1%84%80%E1%85%B5%E1%84%83%E1%85%B3%E1%86%AF.jpg"


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    sold = serializers.SerializerMethodField()
    followers = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'nickname', 'email', 'profile', 'reviews', 'sold', 'followers']

    def get_sold(self, obj):
        sold_products = Product.objects.filter(seller=obj, sold=True)
        return sold_products.count()

    def get_reviews(self, obj):
        return 0

    def get_followers(self, obj):
        followers = Follow.objects.filter(_to=obj)
        return followers.count()

    def get_profile(self, obj):
        try:
            profile = Profile.objects.get(user=obj)
            return ThumbnailSerializer(profile).data
        except:
             return {"thumbnail_img":"http://1567e764.ngrok.io/media/%EC%86%90%EC%A4%80%ED%98%81%20/profile/%E1%84%8C%E1%85%A9%E1%84%8C%E1%85%A6_%E1%84%92%E1%85%A9%E1%84%85%E1%85%A1%E1%86%BC%E1%84%8B%E1%85%B5_%E1%84%80%E1%85%B3%E1%84%85%E1%85%B5%E1%84%80%E1%85%A9_%E1%84%86%E1%85%AE%E1%86%AF%E1%84%80%E1%85%A9%E1%84%80%E1%85%B5%E1%84%83%E1%85%B3%E1%86%AF.jpg"}


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'thumbnail_img', 'background_img','address1','address2','introduce']