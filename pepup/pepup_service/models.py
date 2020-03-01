from django.db import models
from django.conf import settings
from api.models import Product


class PepupMan(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pepupman')
    is_pepupman = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.CharField(max_length=300, null=True, blank=True)
    address = models.TextField()


class PepupService(models.Model):
    """
    pepup service 관리하는 모델입니다. 해당 모델에 pepupman, user를 할당한 후,
    pepupman 의 일 처리 과정을 기록합니다.
    정산이 완료되고 판매가 완료되면 box_status=9, is_done=True.
    """
    PEPUP_GOT_APPLY = 0
    PEPUP_ASSIGN_PEPUPMAN = 1

    PEPUP_SEND_BOX_TO_USER = 2
    USER_SEND_BOX_TO_PEPUPMAN = 21  # if we can parse box delivery

    PEPUPMAN_GOT_CLOTHES_BOX = 3
    PEPUPMAN_CHECKED_CLOTHES_STATE = 31  # check quantity, quality
    PEPUPMAN_START_REGISTER = 32
    PEPUPMAN_ON_WORKING = 33

    PEPUPMAN_FINISIED_WORKING = 9

    BOX_STATUE = [
        (PEPUP_GOT_APPLY, '신청받음'),
        (PEPUP_ASSIGN_PEPUPMAN, 'pepupman 할당'),
        (PEPUP_SEND_BOX_TO_USER, '신청자에게 박스 발송'),
        (USER_SEND_BOX_TO_PEPUPMAN, 'pepupman에게 박스 발송'),
        (PEPUPMAN_GOT_CLOTHES_BOX, 'pepupman 박스 수령'),
        (PEPUPMAN_CHECKED_CLOTHES_STATE, 'pepupman 물건 확인'),
        (PEPUPMAN_START_REGISTER, 'pepupman 물건 등록 시작'),
        (PEPUPMAN_ON_WORKING, 'pepupman 촬영 및 판매 중'),
        # 정산 모델을 따로 셍성. 모든 상품에 대해 정산이 완료되면 하단 상태로 변환
        (PEPUPMAN_FINISIED_WORKING, 'pepupman 촬영 및 판매 정산 완료'),
     ]

    box_status = models.IntegerField(choices=BOX_STATUE, default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pepup_services")
    quantity = models.PositiveIntegerField()
    pepupman = models.ForeignKey(PepupMan, on_delete=models.CASCADE, related_name="manager", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)


class PepupServiceManager(models.Model):
    """
    pepupman 이 상품을 등록할 시 한 상품당 생성되는 관리 모델입니다.
    이 모델을 통해 상품 정산을 관리하고, 어떤 제품이 빨리 팔리는지 확인합니다.

    """
    service = models.ForeignKey(PepupService, on_delete=models.CASCADE, related_name="settle_account")
    products = models.OneToOneField(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="pepup_services")
    settle_accounts = models.BooleanField(default=False, help_text="정산시 True")
    settlement_amount = models.IntegerField(null=True, blank=True, help_text="정산 금액")
    settle_acccounts_time = models.DateTimeField(null=True, blank=True, help_text="정산 날짜")
    settle_accounts_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    sold_time = models.DateTimeField(null=True, blank=True)  # 판매 완료 시각

