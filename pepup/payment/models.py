from django.core.validators import MinValueValidator,MaxValueValidator
from django.db import models
from django.conf import settings


class Commission(models.Model):
    rate = models.FloatField(verbose_name='수수료', validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    info = models.TextField(verbose_name='내용')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Payment(models.Model):
    STATUS = [
        (0, '결제대기'),
        (1, '결제완료'),
        (2, '결제승인전'),
        (3, '결제승인중'),
        (20, '결제취소'),
        (-20, '결제취소실패'),
        (-30, '결제취소진행중'),
        (-1, '오류로 인한 결제실패'),
        (-2, '결제승인실패')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='유저')
    receipt_id = models.CharField(max_length=100, verbose_name='영수증키')
    status = models.IntegerField(choices=STATUS, verbose_name='결제상태', default=0)

    price = models.IntegerField(verbose_name='결제금액', null=True)
    name = models.CharField(max_length=100, verbose_name='대표상품명')
    tax_free = models.IntegerField(verbose_name='면세금액', null=True)
    remain_price = models.IntegerField(verbose_name='남은금액', null=True)
    remain_tax_free = models.IntegerField(verbose_name='남은면세금액',null=True)
    cancelled_price = models.IntegerField(verbose_name='취소금액', null=True)
    cancelled_tax_free = models.IntegerField(verbose_name='취소면세금액', null=True)
    pg = models.TextField(default='inicis', verbose_name='pg사')
    method = models.TextField(verbose_name='결제수단')
    payment_data = models.TextField(verbose_name='raw데이터')
    requested_at = models.DateTimeField(blank=True, null=True)
    purchased_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        if self.name:
            return self.name
        else:
            return

# todo: payment on delete -> setnull
class Deal(models.Model):  # 돈 관련 (스토어 별로)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='Deal_seller')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='Deal_buyer')
    payment = models.ForeignKey(Payment, null=True, on_delete=models.CASCADE)
    total = models.IntegerField(verbose_name='결제금액')
    remain = models.IntegerField(verbose_name='잔여금')  # 수수료계산이후 정산 금액., 정산이후는 0원, 환불시 감소 등.
    delivery_charge = models.IntegerField(verbose_name='배송비')


# todo: payment on delete -> setnull
class Delivery(models.Model):
    STEP0 = 'step0'
    STEP1 = 'step1'
    STEP2 = 'step2'
    STEP3 = 'step3'
    STEP4 = 'step4'
    STEP5 = 'step5'

    states = [
        (STEP0, '운송장입력전'),
        (STEP1, '상품인수'),
        (STEP2, '상품이동중'),
        (STEP3, '배달지도착'),
        (STEP4, '배송출발'),
        (STEP5, '배송완료')
    ]

    codes = [
        ('04', 'CJ대한통운'), ('05', '한진택배'), ('08', '롯데택배'),
        ('01', '우체국택배'), ('06', '로젠택배'), ('11', '일양로지스'),
        ('12', 'EMS'), ('14', 'UPS'), ('26', 'USPS'),
        ('22', '대신택배'), ('23', '경동택배'), ('32', '합동택배'),
        ('46', 'CU 편의점택배'), ('24', 'CVSnet 편의점택배s'),
        ('16', '한의사랑택배'), ('17', '천일택배'), ('18', '건영택배'),
        ('28', 'GSMNtoN'), ('29', '에어보이익스프레스'), ('30', 'KGL네트웍스'),
        ('33', 'DHLarcel'), ('37', '판토스'), ('38', 'ECMS Express'),
        ('40', '굿투럭'), ('41', 'GSI Express'), ('42', 'CJ대한통운 국제특송'),
        ('43', '애니트랙'), ('44', '호남택배'), ('47', '우리한방택배'),
        ('48', 'ACI Express'), ('49', 'ACE Express'), ('50', 'GPS Logix'),
        ('51', '성원글로벌카고'), ('52', '세방'), ('55', 'EuroParcel'),
        ('56', 'KGB택배'), ('57', 'Cway Express'), ('58', '하이택배'),
        ('59', '지오로직'), ('60', 'YJS글로벌(영국)'), ('63', '은하쉬핑'),
        ('64', 'FLF퍼레버택배'), ('65', 'YJS글로벌(월드)'), ('66', 'Giant Network Group'),
        ('70', 'LOTOS CORPORATION'), ('71', 'IK물류'), ('72', '성훈물류'), ('73', 'CR로지텍'),
        ('74', '용마로지스'), ('75', '원더스퀵'), ('76', '대ress'), ('78', '2FastExpress'),
        ('99', '롯데택배 해외특송')
    ]  # 택배사코드

    deal = models.OneToOneField(Deal, null=True, on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='receiver')
    address = models.TextField(verbose_name='배송지')
    memo = models.TextField(default='', verbose_name='배송메모')
    mountain = models.BooleanField(verbose_name='산간지역유무', default=False)

    state = models.TextField(choices=states,default='step0')
    code = models.TextField(choices=codes, verbose_name='택배사코드')
    number = models.TextField(verbose_name='운송장번호')


from api.models import Product


class Trade(models.Model):  # 카트, 상품 하나하나당 아이디 1개씩

    STATUS = [
        (1, '결제전'),
        (2, '결제완료'),  # payment/done/ 처리시 바뀜 = 배송전 , noti 날려주기.
        (3, '배송중'),     # 운송장번호 입력시 바꿔줌
        (4, '배송완료'),
        (5, '거래완료'),  # 셀러한테 noti 날려주기. // 리뷰남겼을떄, 운송장 번호 5일 후 (자동구매확정)
        (6, '정산완료'),  # 정산처리 후 admin 필요
        (-1, '환불신청'),
        (-2, '환불승인'),
        (-3, '환불완료'),
        (-20, '환불반려'),
    ]

    deal = models.ForeignKey(Deal, blank=True, null=True, on_delete=models.SET_NULL)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='Trade_seller')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='Trade_buyer')
    status = models.IntegerField(choices=STATUS, default=1)
    # todo: status : 결제, 배송, success, refund


class TradeLog(models.Model):
    STATUS = [
        (1, '결제전'),
        (2, '결제완료'),
        (3, '배송중'),
        (4, '배송완료'),
        (5, '거래완료'),
        (6, '정산완료'),
        (-1, '환불신청'),
        (-2, '환불승인'),
        (-3, '환불완료'),
        (-20, '환불반려'),
    ]

    trade = models.ForeignKey(Trade, on_delete=models.CASCADE)
    log = models.TextField()
    status = models.IntegerField(choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)


class WalletLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    amount = models.IntegerField()
    log = models.TextField(verbose_name='로그')
    deal = models.ForeignKey(Deal, blank=True, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)