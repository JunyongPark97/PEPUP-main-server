from .forms import RegisterForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework import status, viewsets
from django.shortcuts import render

from .models import Register
from .serializers import RegisterSerializer


def home(request):
    return render(request, 'landing.html')


class LandingViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Register.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny, ]

    @action(methods=['get'], detail=False)
    def apply(self, request):
        print('asdasd')
        return render(request, 'register.html')

    @action(methods=['post'], detail=False)
    def register(self, request):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=['get'], detail=False)
    def sell_intro(self, request):
        return render(request, 'sell_intro.html')

    @action(methods=['get'], detail=False)
    def success(self, request):
        return render(request, 'success.html')
