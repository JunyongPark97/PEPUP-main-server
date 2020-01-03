from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate, get_user_model
from .models import User, PhoneConfirm
from .utils import SMSManager
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

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
