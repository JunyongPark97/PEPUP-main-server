from django.contrib.auth import (
    login as django_login,
    logout as django_logout
)
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import mixins

# allauth social
from allauth.socialaccount.providers.kakao.views import KakaoOAuth2Adapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_framework.viewsets import ViewSetMixin

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
    ChatUserInfoSerializer)
from accounts.socialserailzers import CustomSocialLoginSerializer
from .utils import create_token, SMSManager, JusoMaster
from accounts.models import PhoneConfirm, User, Profile, SmsConfirm, Address
import requests


class AccountViewSet(viewsets.GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer
    token_model = Token

    def process_login(self):
        django_login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')

    def get_response_serializer(self):
        response_serializer = TokenSerializer
        return response_serializer

    @action(methods=['get'], detail=False)
    def check_userinfo(self, request):
        """
        :method: GET
        :param request: header token or not
        :return: status
        """
        if request.user.is_anonymous:
            return Response({'code': -1}, status=status.HTTP_200_OK)
        if not hasattr(request.user, 'phone_confirm'):
            return Response({'code': -5}, status=status.HTTP_200_OK)
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
        response = Response({'code': 1, 'status': '로그인에 성공하였습니다.', 'token':self.token.key, 'pk':self.user.id}, status=status.HTTP_200_OK)
        return response

    @action(methods=['post'],detail=False)
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
            return Response({'code': 2, 'status': '닉네임이 없습니다.', 'token': self.token.key, 'pk':self.user.id}, status=status.HTTP_200_OK)
        return self.get_response()

    @action(methods=['post'], detail=False)
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

    @action(methods=['post'], detail=False)
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

    @action(methods=['post'], detail=False)
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
        if self.request.user.is_anonymous:
            try:
                self.user = User.objects.get(phone=self.phone)
            except User.DoesNotExist:
                self.user = User.objects.create(phone=self.phone)
        else:
            self.user = self.request.user
            self.user.phone = self.phone
            self.user.save()
        self.token = create_token(self.token_model, self.user)
        try:
            phoneconfirm = PhoneConfirm.objects.get(user=self.user)

            # 5분 세션 지났을 경우, timeout -> delete phoneconfirm
            # 아닐 경우, 기존 key 다시 전달
            if phoneconfirm.is_confirmed:
                if not self.user.email:
                    phoneconfirm.delete()
                    self.send_sms()
                else:
                    self.response = Response({"code": -3, "status": _("이미 승인되었습니다")}, status=status.HTTP_200_OK)
            elif PhoneConfirmSerializer().timeout(phoneconfirm):
                self.send_sms()
                self.response = Response(
                    {"code": -2, "status": _("세션이 만료되었습니다. 새로운 key를 보냅니다."), "token": self.token.key, 'pk': self.user.id},
                    status=status.HTTP_200_OK)
            else:
                self.response = Response({
                    "code": -1,
                    "status": _("이미 전송하였습니다"),
                    "token": self.token.key,
                    'pk': self.user.id}, status=status.HTTP_200_OK
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
                    "token": self.token.key,
                    "pk": self.user.id
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
                if not self.user.email:
                    self.response = Response({'code': 1, "status": _("Successfully_confirmed")},
                                             status=status.HTTP_200_OK)
                else:
                    self.response = Response({'code': 2, "status": "access from social"},
                                             status=status.HTTP_200_OK)
            else:
                # todo: fix status 400 to 200
                self.response = Response({'code': -1, "status": _("key does not match")},
                                         status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
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
            if self.user.is_anonymous:
                self.response = Response({'code': -5, 'status': _('로그인이 되지 않았습니다.')}, status=status.HTTP_200_OK)
            else:
                self._confirmsms()
        else:
            self.response = Response({'code': -10, 'status': _('요청 바디가 없습니다.')}, status=status.HTTP_200_OK)
        return self.response

    @action(methods=['post'], detail=False)
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

    @action(methods=['get', 'post'], detail=False, permission_classes=[IsAuthenticated])
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

    def _find_email(self):
        """
        called from find_email
        :return: nothing
        1. if user exist with request phone, check sms sent
            -> if not sent, set sendsms
        """
        try:
            smsconfirm = SmsConfirm.objects.get(user=self.user, for_email=True)
            serializer = SmsConfirmSerializer(smsconfirm)
            if serializer.timeout(smsconfirm):
                self.response = Response({"code": -2, 'status': '세션 만료'},status=status.HTTP_200_OK)
            else:
                self.response = Response({"code": -1, 'status': 'already sent'}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            self.smsmanager = SMSManager(user=self.user)
            self.smsmanager.set_content()
            self.smsmanager.create_smsconfirm(for_email=True)
            self.smsmanager.send_sms()
            self.response = Response({'code': 1, 'status': _("Successfully sent")})

    def _find_email_check(self):
        try:
            smsconfirm = SmsConfirm.objects.get(user=self.user, for_email=True)
            if smsconfirm.key == self.confirm_key:
                smsconfirm.delete()
                self.response = Response(
                    {"code": 1, "status": "인증이 성공하였습니다.", 'email': self.user.email},
                    status=status.HTTP_200_OK
                )
            else:
                self.response = Response({'code': -1, 'status': 'key does not match'})
        except ObjectDoesNotExist:
            self.response = Response({'code': -4, 'status': 'no smsconfirm'}, status=status.HTTP_200_OK)

    # todo: response -> code, status
    @action(methods=['post'], detail=False)
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

        try:
            self.user = User.objects.get(phone=request.data.get('phone'))
        except ObjectDoesNotExist:
            return Response({'code': -5, 'status': 'user not found'}, status=status.HTTP_404_NOT_FOUND)

        # 컨펌 key 대조
        if self.confirm_key and self.phone:
            self._find_email_check()

        # 컨펌 key 요청
        elif request.data.get('phone'):
            self._find_email()
        else:
            self.response = Response({'code': -10, 'status': 'invaild request'}, status=status.HTTP_200_OK)
        return self.response

    def reset_password_sms_send(self):
        try:
            smsconfirm = SmsConfirm.objects.get(user=self.user, for_password=True)
            serializer = SmsConfirmSerializer(smsconfirm)

            # check timeout
            if serializer.timeout(smsconfirm):
                self.response = Response({'code': -2, "status": _("Session_finished")},
                                         status=status.HTTP_200_OK)
            else:
                self.response = Response({'code': -1, 'status': _("Is Already send")},
                                         status=status.HTTP_200_OK)
        except SmsConfirm.DoesNotExist:
            self.smsmanager = SMSManager(user=self.user)
            self.smsmanager.set_content()
            self.smsmanager.create_smsconfirm(for_password=True)
            if not self.smsmanager.send_sms(to=self.user.phone):
                self.response = Response({"code": -20, 'status': _('메세지 전송오류입니다.')}, status.HTTP_400_BAD_REQUEST)
            else:
                self.smsmanager.send_sms()
                self.response = Response({'code': 1, 'status': _("Successfully sent")},status=status.HTTP_200_OK)

    def reset_password_sms_confirm(self):
        try:
            smsconfirm = SmsConfirm.objects.get(user=self.user, for_password=True)
        except SmsConfirm.DoesNotExist:
            self.response = Response({'code': -3,'status': 'no smsconfirm'}, status=status.HTTP_200_OK)
            return

        if smsconfirm.key == self.confirm_key:
            smsconfirm.delete()
            token = create_token(self.token_model, self.user)
            self.response = Response({
                'code': 1, 'status': 'success', 'token': token.key, 'pk': self.user.id
            }, status=status.HTTP_200_OK)
        else:
            self.response = Response({'code': -1, 'status': 'key does not match'},status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def reset_password_sms(self, request):
        """
        method: POST
        :param request: email and phone
        :return: code and status
        """
        self.confirm_key = request.data.get('confirm_key')
        self.phone = request.data.get('phone')
        self.email = request.data.get('email')

        if self.phone and self.email:
            try:
                self.user = User.objects.get(phone=self.phone, email=self.email)
            except User.DoesNotExist:
                return Response({'code': -4, 'status': '해당정보의 유저가 없습니다'}, status =status.HTTP_200_OK)
            if not self.confirm_key:
                self.reset_password_sms_send()
            else:
                self.reset_password_sms_confirm()
        else:
            self.response = Response({'code': -10, 'status': '요청바디가 없습니다.'}, status=status.HTTP_200_OK)
        return self.response

    @action(methods=['post'], detail=False)
    def reset_password(self, request):
        """
        method:POST
        :param request:
        :return:
        """
        self.request = request
        self.user = request.user
        if self.user.is_anonymous:
            return Response({'code': -3, 'status': '로그인을 해주세요'}, status=status.HTTP_200_OK)
        if request.data.get('password'):
            if request.data.get('password').__len__()>=8:
                serializer = SignupSerializer(self.user, data=self.request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({'code': 1, 'status': '비밀번호가 성공적으로 변경되었습니다'}, status=status.HTTP_200_OK)
                return Response({'code': -1, 'status': '요청 body의 key가 잘못되었습니다.'}, status=status.HTTP_200_OK)
            else:
                return Response({'code': -2, 'status': '8자 이상의 비밀번호를 입력해주세요'},status=status.HTTP_200_OK)
        else:
            return Response({'code': -4, 'status': '요청바디가 없습니다.'}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False)
    def check_store(self, request):
        user = request.user
        if hasattr(user, 'delivery_policy'):
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def chat_userinfo(self, request):
        user = request.user

        serializer = ChatUserInfoSerializer(user)

        return Response(serializer.data, status=status.HTTP_200_OK)



### ADDRESS SEARCH VIEWSET ###

def search_address_page(request):
    return render(request, 'address.html')

class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    permission_classes = [IsAuthenticated, ]
    serializer_class = AddressSerializer

    @action(methods=['post'], detail=False)
    def search(self, request, currentpage=1):
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

    def retrieve(self, request, *args, **kwargs):
        """
        method: GET
        :param request: header token
        :return:
        """
        return super(AddressViewSet, self).retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        method: GET
        :param request: header token
        :return: status and address
        """
        user = request.user
        addresses = self.get_queryset().filter(user=user).order_by('-updated_at')
        serializer = self.get_serializer(addresses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        method: DELETE
        :param request: header token
        :return: status
        """
        return super(AddressViewSet, self).destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Method: POST
        :param request: header token and bodyaddress
        :return: code and status
        """
        user = request.user
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors)

        # others recent = False
        self.get_queryset().filter(user=user).update(recent=False)

        serializer.save(user=user)

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=['put'], detail=True)
    def recent(self, request, *args, **kwargs):
        obj = self.get_object()
        self.get_queryset().update(recent=False)
        obj.recent = True
        obj.save()
        return Response(status=status.HTTP_206_PARTIAL_CONTENT)


### SOCIAL LOGIN VIEWSET ###
class SocialUserViewSet(ViewSetMixin, SocialLoginView):
    serializer_class = CustomSocialLoginSerializer

    def _login(self):
        self.user = self.serializer.validated_data['user']
        self.token = create_token(self.token_model, self.user)
        if getattr(settings, 'REST_SESSION_LOGIN', True):
            self.process_login()

    @action(methods=['post'], detail=False)
    def login(self, request):
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data,
                                              context={'request': request})

        self.serializer.is_valid(raise_exception=True)
        self._login()
        self.create()
        response = self.get_response()
        response.data['pk'] = self.user.id
        return response

    @action(methods=['get'],detail=False)
    def callback(self, request):
        return Response(None, status=status.HTTP_200_OK)

    def create(self):
        # process signup
        pass


class CustomKakaoOAuth2Adapter(KakaoOAuth2Adapter):
    def complete_login(self, request, app, token, **kwargs):
        headers = {'Authorization': 'Bearer {0}'.format(token.token)}
        resp = requests.get(self.profile_url, headers=headers)
        extra_data = resp.json()
        # create를 위해 제가 추가한 것
        print(extra_data)
        self.extra_data = extra_data
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


class KakaoUserViewSet(SocialUserViewSet):
    adapter_class = CustomKakaoOAuth2Adapter

    # https://developers.kakao.com/docs/restapi/user-management#사용자-정보-요청
    # 유저 데이터 넣기 : nickname, profile
    def create(self):
        print('test!!')
        userdata = self.serializer.extra_data['kakao_account'].get('profile')
        nickname = userdata.get('nickname')
        if not hasattr(self.user, 'profile'):
            Profile.objects.create(user=self.user)
        if nickname:
            self.user.nickname = nickname
            self.user.save()


class GoogleUserViewSet(SocialUserViewSet):
    # google 과 naver는 닉네임과 프로필을 받아야함!
    adapter_class = GoogleOAuth2Adapter

    def create(self):
        print('test!!')
        userdata = self.serializer.extra_data['google_account'].get('profile')
        nickname = userdata.get('nickname')
        if not hasattr(self.user, 'profile'):
            Profile.objects.create(user=self.user)
        if nickname:
            self.user.nickname = nickname
            self.user.save()



class MySocialAccountAdapter(DefaultSocialAccountAdapter, KakaoOAuth2Adapter):

    def complete_login(self, request, app, token, **kwargs):
        headers = {'Authorization': 'Bearer {0}'.format(token.token)}
        resp = requests.get(self.profile_url, headers=headers)
        extra_data = resp.json()
        # create를 위해 제가 추가한 것
        print(extra_data)
        self.extra_data = extra_data
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id:
            return
        try:
            customer = User.objects.get(email=user.email)  # if user exists, connect the account to the existing account and login
            sociallogin.state['process'] = 'connect'
            perform_login(request, customer, 'none')
        except User.DoesNotExist:
            pass
