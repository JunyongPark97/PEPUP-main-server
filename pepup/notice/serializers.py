from django.contrib.auth import get_user_model
from datetime import datetime
from rest_framework import serializers

from notice.models import Notice, FAQ, Official, NoticeBanner

User = get_user_model()


class NoticeSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Notice
        fields = ('id', 'title', 'content', 'important', 'created_at', 'updated_at')
        read_only_field = ('title', 'content', 'created_at', 'updated_at')

    def get_created_at(self, obj):
        created_at = obj.created_at.strftime('%Y-%m-%d')
        return created_at

    def get_updated_at(self, obj):
        updated_at = obj.updated_at.strftime('%Y-%m-%d')
        return updated_at


class NoticeBannerSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    notice_id = serializers.SerializerMethodField()

    class Meta:
        model = NoticeBanner
        fields = ('id','banner_url', 'notice_id', 'created_at', 'updated_at')
        read_only_field = ('banner_url', 'created_at', 'updated_at')

    def get_created_at(self, obj):
        created_at = obj.created_at.strftime('%Y-%m-%d')
        return created_at

    def get_updated_at(self, obj):
        updated_at = obj.updated_at.strftime('%Y-%m-%d')
        return updated_at

    def get_notice_id(self, obj):
        if obj.notice:
            return obj.notice.id
        return None



class FAQSerializer(serializers.ModelSerializer):
    updated_at = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = ('id', 'title', 'content', 'created_at', 'updated_at')
        read_only_field = ('title', 'content', 'created_at', 'updated_at')

    def get_created_at(self, obj):
        created_at = obj.created_at.strftime('%Y-%m-%d')
        return created_at

    def get_updated_at(self, obj):
        updated_at = obj.updated_at.strftime('%Y-%m-%d')
        return updated_at


class OfficialSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Official
        fields = ('id', 'content', 'created_at', 'updated_at')
        read_only_field = ('title', 'content', 'created_at', 'updated_at')

    def get_created_at(self, obj):
        created_at = obj.created_at.strftime('%Y-%m-%d')
        return created_at

    def get_updated_at(self, obj):
        updated_at = obj.updated_at.strftime('%Y-%m-%d')
        return updated_at
