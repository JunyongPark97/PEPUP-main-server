# -*- encoding: utf-8 -*-
from django.utils import timezone
from rest_framework import serializers
from core.serializers import CommaSeparatedUUIDField, CommaSeparatedIntegerListField
from notifications.models import FCMDevice, NotificationUserLog
from .models import Notification


class NotificationCreateSerializer(serializers.ModelSerializer):
    """
    대량 발송을 위한 rest page 입니다.
    """
    image = serializers.CharField(required=False,
                                  default="https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/media/pepup.png")
    icon = serializers.CharField(required=False,
                                 default="")
    link = serializers.CharField(required=False, default="mypepup.com/api/products/")
    extras = serializers.CharField(required=False, help_text="nickname 정보나 button 정보를 넣습니다.")
    list_user = CommaSeparatedIntegerListField(help_text="user id list를 ,로 구분해서 넣습니다. (5000개 이하로) ex) 12,71,81")

    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'content', 'action', 'image', 'icon', 'target', 'created_at', 'list_user',
            'link',
            'extras')

    def create(self, validated_data):
        from notifications.tools import send_push_async
        from accounts.models import User
        extras = validated_data.pop('extras', {})
        list_user_ids = validated_data.pop('list_user', [])
        list_user = User.objects.filter(id__in=list_user_ids)
        notification = Notification.objects.create(**validated_data)
        send_push_async(list_user=list_user, notification=notification, extras=extras)
        return list_user.count()


class NotificationSerializer(serializers.ModelSerializer):
    queryset = Notification.objects.all()
    read_at = serializers.SerializerMethodField()
    deleted_at = serializers.SerializerMethodField()
    extras = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            'id', 'action', 'title', 'content', 'read_at', 'target', 'created_at', 'link', 'image', 'icon',
            'big_image', 'deleted_at', 'extras')
        read_only_field = ('created_at')

    def get_read_at(self, obj):
        try:
            user = self.context['request'].user
            user_log = obj.user_logs.filter(user=user).first()
            return user_log.read_at
        except:
            return None

    def get_deleted_at(self, obj):
        try:
            user = self.context['request'].user
            user_log = obj.user_logs.filter(user=user).first()
            return user_log.deleted_at
        except:
            return None

    def get_extras(self, obj):
        try:
            user = self.context['request'].user
            user_log = obj.user_logs.filter(user=user).first()
            return user_log.extras
        except:
            user_log = obj.user_logs.first()
            if user_log:
                return user_log.extras
            else:
                return {}


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ('reg_id', 'dev_id')


class NotificationReadSerializer(serializers.Serializer):
    outside = serializers.BooleanField(default=False)

    class Meta:
        fields = ('outside', )


class NotificationBadgeSerializer(serializers.Serializer):
    last_read_at = serializers.CharField(default="", initial="2020-02-04 12:00:00",
                                         help_text='알림을 마지막으로 확인한 시각을 입력해 주세요. ex) 2017-01-01 10:10:00')
    last_read_format = serializers.CharField(default="%Y-%m-%d %H:%M:%S",
                                             initial="%Y-%m-%d %H:%M:%S", help_text='date format')

    class Meta:
        fields = ('last_read_at', 'last_read_format')
