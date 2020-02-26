from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework import status, viewsets
from django.shortcuts import render
from rest_framework.views import APIView

from .models import Register
from .serializers import RegisterSerializer


def home(request):
    return render(request, 'landingHome.html')

def apply(request):
    return render(request, 'register.html')

def sell_intro(request):
    return render(request, 'landing.html')

def success(request):
    return render(request, 'success.html')


class LandingViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Register.objects.all()
    serializer_class = RegisterSerializer

    @action(methods=['get'], detail=False)
    def apply(self, request):
        print('asdasd')
        return render(request, 'register.html')

    @action(methods=['post'], detail=False)
    def register(self, request):
        print('-asdasd')
        data = request.data.copy()
        print(data)
        serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=['get'], detail=False)
    def sell_intro(self, request):
        return render(request, 'landing.html')

    @action(methods=['get'], detail=False)
    def success(self, request):
        return render(request, 'success.html')


class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        print('-asdasd')
        data = request.data.copy()
        print(data)
        serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)