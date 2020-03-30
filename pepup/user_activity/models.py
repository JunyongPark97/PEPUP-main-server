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
        # 100 ~ 구매관련 for buyer
        (100, '첫 주문시, 결제가 완료됨'),
        (101, '판매자 운송장 입력시, 배송 출발+수령확인버튼'), # 무조건 있는 상황
        (102, '판매자 운송장 입력후 5일+수령확인x, 배송완료+리뷰작성버튼'),
        (190, '결제오류, 결제취소됨'),
        # (103, '수령확인시, 배송완료+리뷰작성버튼'), # create하지 않고 101상태에서 return condition만 업데이트

        # 200 ~ 판매관련 for seller
        (200, '결제 완료시, 주문되었음+운송장번호버튼'),
        (201, '거래 완료시, 거래완료되었음 정산예정'), # 리뷰 작성시
        (202, '판매자 운송장 입력후 5일+수령확인x, 거래완료되었음 정산예정'), # 5일뒤 자동생성
        (203, '정산 시, 정산됨'),

        (3, '상품등록관련'),
        (4, '장바구니관련'),
        (5, '팔로우관련'),
        (6, '공지사항'),
        (7, '이벤트'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_logs")
    status = models.IntegerField(choices=LOG_STATUS)
    content = models.CharField(max_length=250, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    big_image_url = models.CharField(max_length=400, null=True, blank=True, help_text="notice 에 들어가는 이미지 url")

    reference = models.ForeignKey('UserActivityReference', on_delete=models.CASCADE, null=True, blank=True, related_name="logs")

    is_active = models.BooleanField(default=True)


class UserActivityReference(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, null=True, blank=True, related_name='log_references')
    follow = models.ForeignKey(Follow, on_delete=models.CASCADE, null=True, blank=True, related_name='log_references')
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, null=True, blank=True, related_name='log_reference')
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, null=True, blank=True, related_name='log_reference')
