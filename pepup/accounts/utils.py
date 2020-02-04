import string
import random
import requests
import json
from accounts.models import PhoneConfirm, WalletLog, SmsConfirm
from api.models import Follow
from rest_framework.authtoken.models import Token
from django.db.models import Sum
from .loader import load_credential
import requests

class SMSManager():
    # todo: accesskey랑 발신번호 및 시크릿 키 초기화 필요
    serviceId = load_credential("serviceId")
    access_key = load_credential("access_key")
    secret_key = load_credential("secret_key")
    _from = load_credential("_from")  # 발신번호
    url = "https://api-sens.ncloud.com/v1/sms/services/{}/messages".format(serviceId)
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'x-ncp-auth-key': access_key,
        'x-ncp-service-secret': secret_key,
    }

    def __init__(self, user):
        self.confirm_key = ""
        self.user = user
        self.body = {
            "type": "SMS",
            "countryCode": "82",
            "from": self._from,
            "to": [],
            "subject": "",
            "content": ""
        }

    def create_instance(self):
        phone_confirm = PhoneConfirm.objects.create(
            user=self.user,
            key=self.confirm_key
        )
        return phone_confirm

    def create_smsconfirm(self,for_email=False,for_password=False):
        smsconfirm = SmsConfirm.objects.create(
            user=self.user,
            key=self.confirm_key,
            for_email=for_email,
            for_password=for_password
        )
        return smsconfirm

    def generate_random_key(self):
            return ''.join(random.choices(string.digits, k=6))

    def set_confirm_key(self):
        self.confirm_key = self.generate_random_key()

    def set_content(self):
        self.set_confirm_key()
        self.body['content'] = "[몽데이크] [인증번호:{}] 인증번호를 입력해주세요".format(self.confirm_key)

    def send_sms(self, to=None):
        if to:
            self.body['to'] = [to]
        elif self.user:
            self.body['to'] = [self.user.phone]
        self.res = requests.post(self.url, headers=self.headers, data=json.dumps(self.body, ensure_ascii=False).encode('utf-8'))
        if self.res.json()['status'] != '200':
            return False
        return True


def generate_random_key(length=10):
    return ''.join(random.choices(string.digits+string.ascii_letters, k=length))


def create_token(token_model, user):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


def get_user(request):
    token_key = request.headers['Authorization'].split(' ')[1]
    try:
        token = Token.objects.get(key=token_key)
        user = token.user
        return user
    except:
        self.response = Response({'status':0})
        return None

def get_follower(user):
    followers = Follow.objects.filter(_to=user)
    return followers


class Cashier:
    def __init__(self, user):
        self.user = user
        self.walletlogs = self.get_logs()
        self.sum = self.sum_logs()

    def get_logs(self):
        return WalletLog.objects.filter(user=self.user)

    def sum_logs(self):
        return self.walletlogs.aggregate(Sum('amount'))['amount__sum']

    def is_validated(self, amount):
        if self.sum_logs() + amount >= 0:
            return True
        return False

    def write_log(self):
        if self.walletlogs:
            pass

    def create_log(self, amount, log='', payment=None):
        if amount < 0:
            if self.is_validated(amount):
                raise ValueError
        newlog = WalletLog(
            user=self.user,
            amount=amount,
            log=log,
        )
        if payment:
            newlog.payment = payment
        newlog.save()
        return newlog


class JusoMaster:
    url = "http://www.juso.go.kr/addrlink/addrLinkApi.do"
    confmKey = 'U01TX0FVVEgyMDIwMDEzMDIxMDA1MDEwOTQyNzQ='

    def search_juso(self, keyword='', currentpage=1, countperpage=10):
        res = requests.post(self.url, data={
            'confmKey': self.confmKey,
            'keyword': keyword,
            'currentPage': currentpage,
            'countPerPage': countperpage,
            'resultType': 'json'
        })
        return (res.json()['results']['common'], res.json()['results']['juso'])