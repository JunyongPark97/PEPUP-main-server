from django.contrib.auth import (
    login as django_login,
    logout as django_logout
)
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.http import JsonResponse

from .serializers import (
    TokenSerializer,
    LoginSerializer,
    PhoneConfirmSerializer,
    SignupSerializer
)
from .permissions import IsOwnerByToken
from .utils import create_token, SMSManager, get_user
from .models import PhoneConfirm, User
from api.models import Product

import json
import requests

from django.http import HttpResponse, JsonResponse
# Create your views here.


class AccountViewSet(viewsets.GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer
    token_model = Token

    def process_login(self):
        django_login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')

    def get_response_serializer(self):
        response_serializer = TokenSerializer
        return response_serializer

    def _login(self):
        self.user = self.serializer.validated_data['user']
        self.token = create_token(self.token_model, self.user)
        self.process_login()

    def get_response(self):
        serializer_class = self.get_response_serializer()
        data = {
            'user': self.user,
            'key': self.token
        }
        serializer = serializer_class(instance=data,
                                      context={'request': self.request})

        response = Response(serializer.data, status=status.HTTP_200_OK)
        return response

    def login(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data,
                                              context={'request': request})
        self.serializer.is_valid(raise_exception=True)

        self._login()
        return self.get_response()

    def logout(self, request):
        self.serializer_class = TokenSerializer
        try:
            request.user.auth_token.delete()
        except (AttributeError, ObjectDoesNotExist):
            key = request.headers['Authorization']
            if key:
                token = Token.objects.get(key=key.split(' ')[1])
                token.delete()
        if getattr(settings, 'REST_SESSION_LOGIN', True):
            django_logout(request)
        response = Response({"detail": _("Successfully logged out.")},
                            status=status.HTTP_200_OK)
        return response

    def signup(self, request):
        self.request = request
        self.serializer = SignupSerializer(data=request.data)
        if self.serializer.is_valid():
            print(self.serializer.validated_data)
            self.user = self.serializer.create(self.serializer.validated_data)
            self.token = create_token(self.token_model, self.user)
            self.process_login()
            return self.get_response()
        return Response(self.serializer.errors)

    def confirmSMS(self, request, confirm_key=None):
        user = get_user(request)

        if confirm_key:
            phoneconfirm = PhoneConfirm.objects.get(user=user)
            serializer = PhoneConfirmSerializer(phoneconfirm)
            if phoneconfirm.is_confirmed:
                response = Response({"status": _("Already confirmed")},
                                    status=status.HTTP_200_OK)
            elif serializer.timeout(phoneconfirm):
                response = Response({"status": _("Session_finished")},
                                    status=status.HTTP_200_OK)
            else:
                if phoneconfirm.key == confirm_key:
                    phoneconfirm.is_confirmed=True
                    phoneconfirm.save()
                    response = JsonResponse(serializer.data)
                else:
                    return Response({"error": _("key does not match")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                phoneconfirm = PhoneConfirm.objects.get(user=user)
                response = Response({"status": _("Already Exist"),
                                     "key": phoneconfirm.key},status=status.HTTP_200_OK)
            except PhoneConfirm.DoesNotExist:
                smsmanager = SMSManager(user)
                smsmanager.send_sms(user.phone)
                response = Response({"status": _("Successfully_send: {}").format(smsmanager.confirm_key)},
                                status=status.HTTP_200_OK)

        return response


class LogoutView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        response = self.logout(request)
        return self.finalize_response(request, response, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.logout(request)

    def logout(self, request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, ObjectDoesNotExist):
            key = request.headers['Authorization']
            if key:
                token = Token.objects.get(key=key.split(' ')[1])
                token.delete()
        if getattr(settings, 'REST_SESSION_LOGIN', True):
            django_logout(request)
        response = Response({"detail": _("Successfully logged out.")},
                            status=status.HTTP_200_OK)
        return response


class SignupView(APIView):
    def post(self,request):
        serializers = SignupSerializer(data=request.data)
        if serializers.is_valid():
            user = serializers.create(serializers.validated_data)
            token = create_token(Token, user)
            return JsonResponse(dict({"token_key": token.key}, **serializers.data))
        return Response(serializers.errors)


class PhoneConfirmView(APIView):
    def post(self, request, confirm_key=None):
        token_key = request.headers['Authorization'].split(' ')[1]
        token = Token.objects.get(key=token_key)
        user = token.user

        if confirm_key:
            phoneconfirm = PhoneConfirm.objects.get(user=user)
            serializer = PhoneConfirmSerializer(phoneconfirm)
            if phoneconfirm.is_confirmed:
                response = Response({"status": _("Already confirmed")},
                                    status=status.HTTP_200_OK)
            elif serializer.timeout(phoneconfirm):
                response = Response({"status": _("Session_finished")},
                                    status=status.HTTP_200_OK)
            else:
                if phoneconfirm.key == confirm_key:
                    phoneconfirm.is_confirmed=True
                    phoneconfirm.save()
                    response = JsonResponse(serializer.data)
                else:
                    return Response({"error": _("key does not match")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                phoneconfirm = PhoneConfirm.objects.get(user=user)
                response = Response({"status": _("Already Exist"),
                                     "key": phoneconfirm.key},status=status.HTTP_200_OK)
            except PhoneConfirm.DoesNotExist:
                smsmanager = SMSManager(user)
                smsmanager.send_sms(user.phone)
                response = Response({"status": _("Successfully_send: {}").format(smsmanager.confirm_key)},
                                status=status.HTTP_200_OK)

        return response
