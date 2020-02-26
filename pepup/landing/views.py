from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.shortcuts import render
from datetime import datetime
from .serializers import RegisterSerializer
from .slack import slack_message


def home(request):
    return render(request, 'landingHome.html')


def apply(request):
    return render(request, 'register.html')


def sell_intro(request):
    return render(request, 'landing.html')


def success(request):
    return render(request, 'success.html')


class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        name = obj.name
        quantity = obj.quantity
        created_at = datetime.strftime(timezone.now(), '%Y-%m-%d %H:%M')
        bank = obj.bank
        account = obj.account
        slack_message('[사이트 대리판매 신청] \n {} 님께서 {}개 신청하셨습니다. (신청일 {}) \n {}, {}'
                      '\n'
                      '바로가기 : http://pepup.world/admin/'
                      .format(name, quantity, created_at, bank, account))
        return Response(status=status.HTTP_201_CREATED)
