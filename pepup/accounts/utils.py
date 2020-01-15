import string
import random
import requests
import json
from .models import PhoneConfirm, WalletLog
from api.models import Follow
from rest_framework.authtoken.models import Token
from django.db.models import Sum

class SMSManager():
    # todo: accesskey랑 발신번호 및 시크릿 키 초기화 필요
    serviceId = "ncp:sms:kr:257791040520:pepup"
    access_key = "03i7TYTJ2juHkLqENoxy"
    secret_key = "fa061bde494543d9a8f4b6db18da9c6c"
    _from = "01077407351"  # 발신번호
    url = "https://api-sens.ncloud.com/v1/sms/services/{}/messages".format(serviceId)
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'x-ncp-auth-key': access_key,
        'x-ncp-service-secret': secret_key,
    }

    def __init__(self, user):
        self.confirm_key = self.generate_random_key()
        self.user = user
        self.body = {
            "type": "SMS",
            "countryCode": "82",
            "from": self._from,
            "to": [],
            "subject": "",
            "content": "[몽데이크] [인증번호:{}] 인증번호를 입력해주세요".format(self.confirm_key)
        }

    def create_instance(self):
        phone_confirm = PhoneConfirm(user=self.user, key=self.confirm_key)
        phone_confirm.save()
        return phone_confirm

    def generate_random_key(self, length=6):
        return ''.join(random.choices(string.digits, k=length))

    def send_sms(self, to=None):
        if not self.body['to']:
            self.body['to'].append(to)
        self.create_instance()
        res = requests.post(self.url, headers=self.headers, data=json.dumps(self.body, ensure_ascii = False).encode('utf-8'))
        return res


def create_token(token_model, user):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


def get_user(request):
    token_key = request.headers['Authorization'].split(' ')[1]
    token = Token.objects.get(key=token_key)
    user = token.user
    return user


def get_follower(user):
    followers = Follow.objects.filter(following_user=user)
    return followers


class Cashier:
    def __init__(self, user):
        self.user = user
        self.walletlogs = WalletLog.objects.filter(user=user)

    def sum_logs(self):
        self.walletlogs.aggregate(Sum('amount'))

    def get_logs(self):
        ret = []
        for item in self.walletlogs:
            ret.append(+item.log)
        return ret

    def is_validated(self, amount):
        if self.sum_logs() + amount >= 0:
            return True
        return False

    def create_log(self, amount, log, payment, refund):
        if amount < 0:
            if self.is_validated(payment):
                raise ValueError
        newlog = WalletLog(
            user=self.user,
            amount=amount,
            log=log,
        )
        if payment:
            newlog.payment = payment
        if refund:
            newlog.refund = refund
        newlog.save()
        return newlog



