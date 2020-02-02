from django.contrib.auth import get_user_model
from datetime import datetime
from rest_framework import serializers

from notice.models import Notice, FAQ, Official

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
