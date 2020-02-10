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
from rest_framework import exceptions
from django.http import JsonResponse

from accounts.serializers import (
    TokenSerializer,
    LoginSerializer,
    PhoneConfirmSerializer,
    SignupSerializer,
    ProfileSerializer,
    SmsConfirmSerializer,
    AddressSerializer,
    SearchAddrSerializer,
    CommonSerializer,
)
from .permissions import IsOwnerByToken
from .utils import create_token, SMSManager, get_user, generate_random_key, JusoMaster
from accounts.models import PhoneConfirm, User, Profile, SmsConfirm, Address
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

    def check_userinfo(self, request):
        """
        :method: GET
        :param request: header token or not
        :return: status
        """
        if request.user.is_anonymous:
            return Response({'code': -1}, status=status.HTTP_200_OK)
        if not request.user.phone_confirm.is_confirmed:
            return Response({'code': -4}, status=status.HTTP_200_OK)
        if request.user.email:
            if request.user.nickname:
                return Response({'code': 1}, status=status.HTTP_200_OK)
            else:
                return Response({'code': -3}, status=status.HTTP_200_OK)
        return Response({'code': -2}, status=status.HTTP_200_OK)

    def _login(self):
        self.user = self.serializer.validated_data['user']
        self.token = create_token(self.token_model, self.user)
        self.process_login()

    def get_response(self):
        response = Response({'code': 1, 'status': '로그인에 성공하였습니다.','token':self.token.key}, status=status.HTTP_200_OK)
        return response

    def login(self, request, *args, **kwargs):
        """
        method: POST
        :param request:
        :param args:
        :param kwargs: email, password
        :return: code, status, token
        """
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data,
                                              context={'request': request})
        self.serializer.is_valid(raise_exception=True)

        self._login()
        if not self.user.nickname:
            return Response({'code': 2, 'status': '닉네임이 없습니다.', 'token': self.token.key}, status=status.HTTP_200_OK)
        return self.get_response()

    def logout(self, request):
        """
        method: post
        :param request:
        :return: code, status
        """
        # todo: fix response key from detail to code and status
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

    def check_email(self, request):
        """
        method: POST
        :param request: email
        :return: code, status
        """
        try:
            User.objects.get(email=request.data.get('email'))
            return Response({'code': -1, 'status': '중복된 이메일입니다. '})
        except User.DoesNotExist:
            return Response({'code': 1, 'status': '사용가능한 이메일입니다.'})

    def check_nickname(self, request):
        """
        method: POST
        :param request: nicknme
        :return: code, status
        """
        try:
            User.objects.get(nickname=request.data.get('nickname'))
            return Response({'code': -1, 'status': '중복된 닉네임입니다. '})
        except User.DoesNotExist:
            return Response({'code': 1, 'status': '사용가능한 닉네임입니다.'})

    def send_sms(self):
        """
        1. check user by phone. if user is not exist, create user
        2. set token
        3. get phoneconfirm if not -> no.4(except), exist -> no.5(try)
        4. create phoneconfirm -> send sms -> set response
        5. if phoneconfirm is confirmed -> set code to -3,
            elif timeout(3 minutes) -> recur send_sms, set response
            else set code to -1
        """
        try:
            self.user = User.objects.get(phone=self.phone)
        except User.DoesNotExist:
            self.user = User.objects.create(phone=self.phone)
        self.token = create_token(self.token_model, self.user)
        try:
            phoneconfirm = PhoneConfirm.objects.get(user=self.user)

            # 5분 세션 지났을 경우, timeout -> delete phoneconfirm
            # 아닐 경우, 기존 key 다시 전달
            if phoneconfirm.is_confirmed:
                if not self.user.email:
                    phoneconfirm.is_confirmed = False
                    self.send_sms()
                else:
                    self.response = Response({"code": -3, "status": _("이미 승인되었습니다")}, status=status.HTTP_200_OK)
            elif PhoneConfirmSerializer().timeout(phoneconfirm):
                self.send_sms()
                self.response = Response(
                    {"code": -2, "status": _("세션이 만료되었습니다. 새로운 key를 보냅니다."), "token": self.token.key},
                    status=status.HTTP_200_OK)
            else:
                self.response = Response({
                    "code": -1,
                    "status": _("이미 전송하였습니다"),
                    "token": self.token.key}, status=status.HTTP_200_OK
                )
        except PhoneConfirm.DoesNotExist:
            smsmanager = SMSManager(user=self.user)
            smsmanager.set_content()
            smsmanager.create_instance()
            if not smsmanager.send_sms(to=self.user.phone):
                self.response = Response({"code": -20, 'status': _('메세지 전송오류입니다.')}, status.HTTP_400_BAD_REQUEST)
            else:
                self.response = Response({
                    "code": 1,
                    "status": _('메세지를 전송하였습니다'),
                    "token": self.token.key
                }, status=status.HTTP_200_OK)

    def _confirmsms(self):
        """
        1. get phoneconfirm
        2. if phoneconfirm is confirm -> set code to -3
            elif timeout -> just set code to -2
        3. if phoneconfirm key match -> update is_confirm to true -> set code to 1
            else -> set code to -1
        """
        # todo: phoneconfirm dose not exist error fix
        phoneconfirm = PhoneConfirm.objects.get(user=self.user)
        serializer = PhoneConfirmSerializer(phoneconfirm)
        if phoneconfirm.is_confirmed:
            self.response = Response({'code': -3, "status": _("Already confirmed")},
                                     status=status.HTTP_200_OK)
        elif serializer.timeout(phoneconfirm):
            self.response = Response({'code': -2, "status": _("Session_finished")},
                                     status=status.HTTP_200_OK)
        else:
            if phoneconfirm.key == self.request.data['confirm_key']:
                phoneconfirm.is_confirmed = True
                phoneconfirm.save()
                self.response = Response({'code': 1, "status": _("Successfully_confirmed")},
                                         status=status.HTTP_200_OK)
            else:
                # todo: fix status 400 to 200
                self.response = Response({'code': -1, "status": _("key does not match")},
                                         status=status.HTTP_200_OK)

    def confirmsms(self, request):
        """
        method: POST
        :param request: phone or (header token and body confirm_key)
        :return:
        with phone
        :send_sms -> code and status, and token if successfully sent
        with confirm_key
        :_confirmsms -> code and status
        """
        self.request = request
        # todo: 유저의 휴대전화 정보가 없을 경우 처리
        if self.request.data.get('phone'):
            self.phone = self.request.data.get('phone')
            self.send_sms()
        elif self.request.data.get('confirm_key'):
            self.user = self.request.user
            self._confirmsms()
        else:
            self.response = Response({'code': -10, 'status': _('요청 바디가 없습니다.')}, status=status.HTTP_400_BAD_REQUEST)
        return self.response

    def signup(self, request):
        """
        method: POST
        :param request: email, password or nickname
        :return: code, status
        1. if user does not login(no header token) -> code -3
        2. if get email -> check email -> if exist -> code -2
            else: check email duplicated -> code -1
        3. is valid -> save -> code 1
        """
        self.user = request.user
        if self.user.is_anonymous:
            return Response({'code': -3, 'status': '로그인을 해주세요'})
        if request.data.get('email'):
            if self.user.email:
                return Response({'code': -2, 'status': 'user의 email이 존재합니다.'})
            try:
                User.objects.get(email=request.data.get('email'))
                return Response({'code': -1, 'status': '중복된 이메일입니다.'})
            except ObjectDoesNotExist:
                pass
        self.serializer = SignupSerializer(self.user, data=request.data, partial=True)
        if self.serializer.is_valid():
            self.serializer.save()
            return Response({'code': 1, 'status': _('Successfully_signup')}, status=status.HTTP_200_OK)
        return Response(self.serializer.errors)

    def get_profile(self):
        try:
            self.profile = Profile.objects.get(user=self.user)
        except:
            self.profile = None

    def _create_and_update_profile(self):
        if self.profile:
            self.serializer = ProfileSerializer(self.profile, data=self.request.data, partial=True)
        else:
            self.serializer = ProfileSerializer(data=self.request.data, partial=True)
        if self.serializer.is_valid():
            self.serializer.save(user=self.user)
            if self.profile:
                self.response = Response({'status': _("Successfully updated")}, status=status.HTTP_200_OK)
            else:
                self.response = Response({'status': _("Successfully created")}, status=status.HTTP_200_OK)
        else:
            self.response = Response(self.serializer.errors)

    # todo: anonymous user fix
    def profile(self, request):
        self.request = request
        self.user = self.request.user
        self.get_profile()
        # profile create and update
        if request.method == 'POST':
            self._create_and_update_profile()
        # profile get
        elif request.method == 'GET':
            self.serializer = ProfileSerializer(self.profile)
            self.response = Response({'profile': self.serializer.data})
        return self.response

    def search_address(self, request, currentpage=1):
        jusomaster = JusoMaster()
        if request.data.get('currentpage'):
            currentpage = request.data.get('currentpage')
        commondata, data = jusomaster.search_juso(
            keyword=request.data.get('keyword'),
            currentpage=currentpage,
            countperpage=10
        )
        common = CommonSerializer(data=commondata)
        serializer = SearchAddrSerializer(data=data, many=True)
        if serializer.is_valid() and common.is_valid():
            return Response({'common': common.data, 'juso': serializer.data})
        return Response(serializer.errors)

    # todo: anonymous user fix
    # todo: response -> code and status, address
    def get_address(self, request):
        """
        method: GET
        :param request: header token
        :return: code, status and address
        """
        self.user = request.user
        queryset = Address.objects.filter(user=self.user)
        serializer = AddressSerializer(queryset, many=True)
        return Response(serializer.data)

    # todo: anonymous user fix
    # todo: response -> code and status
    def delete_address(self, request):
        """
        method: POST
        :param request: header token
        :return: code and status
        """
        self.user = request.user
        try:
            address = Address.objects.get(pk=request.data.get('pk'))
        except ObjectDoesNotExist:
            return Response({'status': _('pk does not match')}, status=status.HTTP_404_NOT_FOUND)
        serializer = AddressSerializer(address)
        if address.user == self.user:
            address.delete()
            return Response({'status': _('Successfully delete')}, status=status.HTTP_200_OK)
        else:
            return Response({'status': _("user does not match")}, status=status.HTTP_401_UNAUTHORIZED)

    # todo: anonymous user fix
    # todo: response -> code and status
    def set_address(self, request):
        """
        Method: POST
        :param request: header token and bodyaddress
        :return: code and status
        """
        self.user = request.user
        serializer = AddressSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(
                user=self.user
            )
            return Response({'status': _("Successfully set address")}, status.HTTP_201_CREATED)
        return Response(serializer.errors)

    def _find_email(self):
        """
        called from find_email
        :return: nothing
        1. if user exist with request phone, check sms sent
            -> if not sent, set sendsms
        """
        try:
            self.user = User.objects.get(phone=self.phone)
            if SmsConfirm.objects.filter(user=self.user, for_email=True):
                self.response = Response({'status': 'already sent'}, status=status.HTTP_208_ALREADY_REPORTED)
            else:
                self.smsmanager = SMSManager(user=self.user)
                self.smsmanager.set_content()
                self.smsmanager.create_smsconfirm(for_email=True)
                self.smsmanager.send_sms()
                self.response = Response({'status': _("Successfully sent: {}".format(self.smsmanager.confirm_key))})

        except ObjectDoesNotExist:
            self.response = Response({'status': 'user not found'}, status=status.HTTP_404_NOT_FOUND)

    # todo: 정리가 필요합니다...
    # todo: response -> code, status
    def find_email(self, request):
        """
        method: POST
        :param request: phone and confirm_key
        :return: code, status, and email
        1. both confirm_key and phone -> check user, smsconfirm and key
        2. just phone -> call _find_email method
        3. nothing -> invaild request
        """
        self.request = request
        self.confirm_key = request.data.get('confirm_key')
        self.phone = request.data.get('phone')
        if self.confirm_key and self.phone:
            try:
                user = User.objects.get(phone=request.data.get('phone'))
            except ObjectDoesNotExist:
                return Response({'code':-1, 'status': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
            try:
                smsconfirm = SmsConfirm.objects.get(user=user, for_email=True)
                print(smsconfirm.key)
                if smsconfirm.key == self.confirm_key:
                    smsconfirm.delete()
                    self.response = Response({'email': user.email}, status=status.HTTP_200_OK)
                else:
                    self.response = Response({'status': 'key does not match'})
            except ObjectDoesNotExist:
                self.response = Response({'status': 'no smsconfirm'}, status=status.HTTP_404_NOT_FOUND)
            elif request.data.get('phone'):
            self.phone = request.data.get('phone')
            self._find_email()
        else:
            self.response = Response({'status': 'invaild request'}, status=status.HTTP_400_BAD_REQUEST)
        return self.response

    def _reset_password_sms(self, user):

        # 첫 인증 시
        if not SmsConfirm.objects.filter(user=user, for_password=True):
            self.smsmanager = SMSManager(user=user)
            self.smsmanager.set_content()
            self.smsmanager.create_smsconfirm(for_password=True)
            self.smsmanager.send_sms()
            self.response = Response({'code': 1, 'status': _("Successfully sent: {}".format(self.smsmanager.confirm_key))})

            return self.response

        smsconfirm = SmsConfirm.objects.filter(user=user, for_password=True).last()
        serializer = SmsConfirmSerializer(smsconfirm)

        # confirmed
        if smsconfirm.is_confirmed:
            self.response = Response({'code': -3, "status": _("Already confirmed")},
                                     status=status.HTTP_200_OK)
        #
        elif serializer.timeout(smsconfirm):
            self.response = Response({'code': -2, "status": _("Session_finished")},
                                     status=status.HTTP_200_OK)

        else:
            self.response = Response({'code': -1, 'status': _("Is Already send"), 'key': smsconfirm.key},
                                     status=status.HTTP_200_OK)

        return self.response

    def reset_password_sms(self, request):
        """
        method: POST
        :param request: email and phone
        :return: code and status
        """
        # check valid request
        if not request.data.get('email') and request.data.get('phone'):
            return Response({'status': 'invaild request'}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        phone = request.data.get('phone')

        # check exist user
        user = User.objects.filter(email=email)
        if not user:
            return Response({'code': 3, 'status': _('존재하지 않는 ID 입니다.')}, status=status.HTTP_204_NO_CONTENT)

        user = user.last()
        user_phone = user.phone

        # check valid phone number
        if not phone == user_phone:
            return Response({'code': 4, 'status': _('맞지않는 전화번호 입니다.')}, status=status.HTTP_400_BAD_REQUEST)

        # send sms for reset password
        self._reset_password_sms(user)
        return self.response

    def reset_password_sms_confirm(self, request):
        """
        method: POST
        :param request: email, phone, confirm_key
        :return: code and status
        """
        # check valid request
        if not request.data.get('confirm_key') and request.data.get('phone') and request.data.get('email'):
            return Response({'status': 'invaild request'}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        phone = request.data.get('phone')
        confirm_key = request.data.get('confirm_key')

        # check exist user
        user = User.objects.filter(email=email)
        if not user:
            return Response({'code': 3, 'status': _('존재하지 않는 ID 입니다.')}, status=status.HTTP_204_NO_CONTENT)
        user = user.last()
        user_phone = user.phone

        # check valid phone number
        if not phone == user_phone:
            return Response({'code': 4, 'status': _('맞지않는 전화번호 입니다.')}, status=status.HTTP_400_BAD_REQUEST)

        try:
            smsconfirm = SmsConfirm.objects.get(user=user, for_password=True)
            print(smsconfirm.key)
            if smsconfirm.key == confirm_key:
                smsconfirm.delete()
                token = create_token(self.token_model, user)

                return Response({'status': 'success',
                                 'token': token.key}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'key does not match'})
        except ObjectDoesNotExist:
            return Response({'status': 'no smsconfirm'}, status=status.HTTP_404_NOT_FOUND)
