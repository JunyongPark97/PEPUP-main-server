from django.shortcuts import render
from django.utils.safestring import mark_safe

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

import json

from chat.models import Room
from accounts.models import User

from chat.serializers import RoomSerializer


class ChatViewSets(viewsets.GenericViewSet):
    queryset = Room.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer

    def list(self, request):
        rooms = Room.objects.filter(user=request.user)
        serailzer = RoomSerializer(rooms, many=True)
        return Response(serailzer.data)

    @action(methods=['post'], detail=False)
    def create_room(self, request):
        pass

    @action(methods=['get'], detail=False)
    def testlistindex(self, request):
        users = User.objects.exclude(pk=request.user.pk)
        rooms = Room.objects.filter(user=request.user)
        return render(request, 'chat/index.html', {'rooms':rooms,'users':users})

    @action(methods=['get', 'post'], detail=True)
    def testroom(self, request, pk):
        another = User.objects.get(pk=pk)
        room = Room.objects.filter(user=another).filter(user=request.user)
        if not room:
            room = Room.objects.create()
            room.user.add(request.user, another)
        else:
            room = room.first()
        return render(request, 'chat/room.html', {
            'room_pk_json': mark_safe(json.dumps(room.pk))
        })


def index(request):
    if request.user.is_authenticated:
        rooms = Room.objects.filter(user=request.user)

    return render(request, 'chat/index.html', {})


def room(request, room_name):
    return render(request, 'chat/room.html', {
        'room_name_json': mark_safe(json.dumps(room_name))
    })