from rest_framework import serializers
from .models import Room
from accounts.models import User
from django.conf import settings


class UserForRoomSerailizer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['nickname']


class RoomSerializer(serializers.ModelSerializer):
    user = UserForRoomSerailizer(many=True)

    class Meta:
        model = Room
        fields = '__all__'