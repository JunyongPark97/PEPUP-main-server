import os
from datetime import timedelta, datetime

from django.db import models
from django.conf import settings

from api.models import Product, Follow
from notice.models import Notice
from payment.models import Deal, Trade


class UserActivityLog(models.Model):
    """
    log 생성
    1. 주문관련: 주문이 완료됨 / 운송장번호 입력됨 / 구매수령 됨
    2. 팔로우한 태그의 상품이 몇개 등록됨
    3. 장바구니 담은 제품이 누군가가 담음
    4. 공지사항
    5. 이벤트
    """
    LOG_STATUS = [
        (0, '주문관련'),
        (1, '상품등록관련'),
        (2, '장바구니관련'),
        (3, '공지사항'),
        (4, '이벤트'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_logs")
    status = models.IntegerField(choices=LOG_STATUS)
    content = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    reference = models.ForeignKey('UserActivityReference', on_delete=models.CASCADE, null=True, blank=True, related_name="logs")


class UserActivityReference(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, null=True, blank=True, related_name='log_references')
    follow = models.ForeignKey(Follow, on_delete=models.CASCADE, null=True, blank=True, related_name='log_references')
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, null=True, blank=True, related_name='log_reference')
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, null=True, blank=True, related_name='log_reference')
