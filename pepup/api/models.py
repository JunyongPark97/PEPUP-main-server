from django.db import models
from django.conf import settings
import math

from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill


# Create your models here.
class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name='브랜드명')

    # todo: 로고 이미지 fields
    def __str__(self):
        return self.name


class GenderDivision(models.Model):
    """
    성별 모델입니다.
    """
    MAN = 1
    WOMAN = 2
    UNISEX = 3
    OTHER = 4

    GENDER = (
        (MAN, 'Man'),
        (WOMAN, 'Woman'),
        (UNISEX, 'Unisex'),
        (OTHER, 'Other'),
    )

    name = models.IntegerField(choices=GENDER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()


class FirstCategory(models.Model):
    """
    대분류 모델입니다.
    """
    gender = models.ForeignKey('GenderDivision', on_delete=models.CASCADE, related_name='category')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "[{}]{}".format(self.gender, self.name)


class SecondCategory(models.Model):
    """
    소분류 모델입니다.
    """
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('FirstCategory', on_delete=models.CASCADE, related_name='second_category')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "[{}]_{}".format(self.parent, self.name)


class Size(models.Model):
    category = models.ForeignKey('FirstCategory', null=True, on_delete=models.CASCADE, related_name='size')
    size_name = models.CharField(max_length=20, help_text="L, M 등과 같은 분류")
    size = models.PositiveIntegerField(help_text='기본 size, 범위가 있다면 최소 사이즈')
    size_max = models.PositiveIntegerField(null=True, blank=True, help_text='사이즈 범위가 있는 경우 최대 사이즈')
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        if self.size_max:
            return "[{}] {}-{}".format(self.category.name, self.size, self.size_max)
        if self.category.name == 'SHOES':
            return "[{}] {} (cm)".format(self.category.name, self.size)
        return "[{}] {}".format(self.category.name, self.size)


class Tag(models.Model):
    tag = models.CharField(max_length=30)

    def __str__(self):
        return self.tag


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='상품명')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name='product', null=True)
    price = models.IntegerField(verbose_name='가격')
    content = models.TextField(verbose_name='설명')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    sold = models.BooleanField(default=False, verbose_name='판매완료')
    on_discount = models.BooleanField(default=False, verbose_name='세일중')
    discount_rate = models.FloatField(default=0, verbose_name='할인율')
    first_category = models.ForeignKey(FirstCategory, on_delete=models.CASCADE, null=True)
    second_category = models.ForeignKey(SecondCategory, on_delete=models.CASCADE, null=True)
    is_refundable = models.BooleanField(default=False)
    tag = models.ManyToManyField(Tag)

    # todo:
    # 환불가능, 사이즈(카테고리화: 남자->XL),

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        return math.ceil(self.price * (1 - self.discount_rate)/100) * 100


def img_directory_path(instance, filename):
    return 'user/{}/products/{}'.format(instance.product.seller.email, filename)


def thumb_directory_path(instance, filename):
    return 'user/{}/products/thumbnail_{}'.format(instance.product.seller.email, filename)


class ProdThumbnail(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    thumbnail = ProcessedImageField(
        upload_to=thumb_directory_path,  # 저장 위치
        processors=[ResizeToFill(350, 350)],  # 사이즈 조정
        format='JPEG',  # 최종 저장 포맷
        options={'quality': 90})


class ProdImage(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images')
    image = models.FileField(upload_to=img_directory_path)


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='liker', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    is_liked = models.BooleanField(default=True)

from django.db.models.functions import Round
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

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='receiver')
    address = models.TextField(verbose_name='배송지')
    memo = models.TextField(default='', verbose_name='배송메모')
    mountain = models.BooleanField(verbose_name='산간지역유무', default=False)

    state = models.TextField(choices=states)
    code = models.TextField(choices=codes, verbose_name='택배사코드')
    number = models.TextField(verbose_name='운송장번호')



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

    price = models.IntegerField(verbose_name='결제금액')
    name = models.CharField(max_length=100, verbose_name='대표상품명')
    tax_free = models.IntegerField(verbose_name='면세금액')
    remain_price = models.IntegerField(verbose_name='남은금액')
    remain_tax_free = models.IntegerField(verbose_name='남은면세금액')
    cancelled_price = models.IntegerField(verbose_name='취소금액')
    cancelled_tax_free = models.IntegerField(verbose_name='취소면세금액')
    pg = models.TextField(blank=True, null=True, verbose_name='pg사')
    method = models.TextField(verbose_name='결제수단')
    payment_data = models.TextField(verbose_name='raw데이터')
    requested_at = models.DateTimeField(blank=True, null=True)
    purchased_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)


class Deal(models.Model):  # 돈 관련 (스토어 별로)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='Deal_seller')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='Deal_buyer')
    payment = models.ForeignKey(Payment, null=True, on_delete=models.CASCADE)
    total = models.IntegerField(verbose_name='결제금액')
    remain = models.IntegerField(verbose_name='잔여금')  # 수수료계산이후 정산 금액., 정산이후는 0원, 환불시 감소 등.
    delivery_charge = models.IntegerField(verbose_name='배송비')
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE)


class Trade(models.Model):  # 카트, 상품 하나하나당 아이디 1개씩
    STATUS = [
        (1, '결제전'),
        (2, '결제완료'),  # = 배송전 , noti 날려주기.
        (3, '배송중'),
        (4, '배송완료'),
        (5, '거래완료'),  # 셀러한테 noti 날려주기. // 리뷰남겼을떄, 운송장 번호 5일 후 (자동구매확정)
        (6, '정산완료'),  # admin 필요
        (-1, '환불신청'),
        (-2, '환불승인'),
        (-3, '환불완료'),
        (-20, '환불반려'),
    ]

    deal = models.ForeignKey(Deal, blank=True, null=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
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


class Follow(models.Model):
    _from = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='_from',
                              on_delete=models.CASCADE)
    _to = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='_to',
                            on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, blank=True, null=True, on_delete=models.CASCADE)
    is_follow = models.BooleanField(default=True)


def review_directory_path(instance, filename):
    return 'user/{}/review/thumbnail_{}'.format(instance.seller.email, filename)


class Review(models.Model):
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reviews', on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_reviews', on_delete=models.CASCADE)
    context = models.CharField(max_length=50, null=True, blank=True)
    satisfaction = models.DecimalField(decimal_places=2, max_digits=4)
    deal = models.OneToOneField('Deal', on_delete=models.CASCADE, related_name='review')
    thumbnail = ProcessedImageField(
        null=True, blank=True,
        upload_to=review_directory_path,  # 저장 위치
        processors=[ResizeToFill(300, 300)],  # 사이즈 조정
        format='JPEG',  # 최종 저장 포맷
        options={'quality': 70})
    created_at = models.DateTimeField(auto_now_add=True)
