from django.db import models
from django.conf import settings


# Create your models here.
class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name='브랜드명')

    # todo: 로고 이미지 fields

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])


class Tag(models.Model):
    tag = models.CharField(max_length=30)

    def __str__(self):
        return self.tag


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='상품명')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    size = models.TextField()
    price = models.IntegerField(verbose_name='가격')
    content = models.TextField(verbose_name='설명')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    sold = models.BooleanField(default=False, verbose_name='판매완료')
    on_discount = models.BooleanField(default=False,verbose_name='세일중')
    discount_rate = models.FloatField(default=0, verbose_name='할인율')
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)
    is_refundable = models.BooleanField(default=False)
    tag = models.ManyToManyField(Tag)
    # todo:
    # 환불가능, 사이즈(카테고리화: 남자->XL),

    class Meta:
        ordering = ['-id']
    def __str__(self):
        return self.name

    def get_cat_list(self):
        k = self.category  # for now ignore this instance method

        breadcrumb = ["dummy"]
        while k is not None:
            breadcrumb.append(k.slug)
            k = k.parent
        for i in range(len(breadcrumb) - 1):
            breadcrumb[i] = '/'.join(breadcrumb[-1:i - 1:-1])
        return breadcrumb[-1:0:-1]

    def get_discount_price(self):
        return self.price * (1-self.discount_rate)

def img_directory_path(instance, filename):
    return 'user/{}/products/{}'.format(instance.product.seller.email,filename)


class ProdThumbnail(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    thumbnail = models.FileField(upload_to=img_directory_path)

    # def save(self, *args, **kwargs):
    #     if self.thumbnail:
    #         self.thumbnail =


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,related_name='liker',on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    is_liked = models.BooleanField(default=True)

    # todo :
    # sold 후 delete 불가능하게!
    # def lock_delete():


class Payment(models.Model):
    STATUS = [
        (0,'결제대기'),
        (1,'결제완료'),
        (2,'결제승인전'),
        (3,'결제승인중'),
        (20,'결제취소'),
        (-20,'결제취소실패'),
        (-30,'결제취소진행중'),
        (-1,'오류로 인한 결제실패'),
        (-2,'결제승인실패')
    ]

    receipt_id = models.CharField(max_length=100, verbose_name='영수증키')
    order_id = models.CharField(max_length=100,verbose_name='주문번호')
    price = models.IntegerField(verbose_name='결제금액')
    name = models.CharField(max_length=100, verbose_name='대표상품명')

    tax_free = models.IntegerField(verbose_name='면세금액')
    remain_price = models.IntegerField(verbose_name='남은금액')
    remain_tax_free = models.IntegerField(verbose_name='남은면세금액')
    cancelled_price = models.IntegerField(verbose_name='취소금액')
    cancelled_tax_free = models.IntegerField(verbose_name='취소면세금액')
    pg = models.TextField(blank=True, null=True,verbose_name='pg사')
    method = models.TextField(verbose_name='결제수단')
    payment_data = models.TextField('raw데이터')
    requested_at = models.DateTimeField(blank=True,null=True)
    purchased_at = models.DateTimeField(blank=True,null=True)
    revoked_at = models.DateTimeField(blank=True,null=True)
    status = models.IntegerField(choices=STATUS, verbose_name='결제상태')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, verbose_name='유저')


class Trade(models.Model):
    STATUS = [
        (0,'결제전'),
        (1,'결제중'),
        (2,'결제완료'),
        (3,'배송중'),
        (4,'배송완료'),
        (5,'거래완료'),
        (-1,'환불'),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='buyer')
    status = models.IntegerField(choices=STATUS, default=0)
    pay_end_date = models.DateTimeField(blank=True, null=True, verbose_name='결제완료시간')
    trade_end_date = models.DateTimeField(blank=True, null=True, verbose_name='거래완료시간')

    # todo: status : 결제, 배송, success, refund


class Delivery(models.Model):
    STEP1 = 'step1'
    STEP2 = 'step2'
    STEP3 = 'step3'
    STEP4 = 'step4'
    STEP5 = 'step5'

    states = [
        (STEP1, '상품인수'),
        (STEP2, '상품이동중'),
        (STEP3, '배달지도착'),
        (STEP4, '배송출발'),
        (STEP5, '배송완료')
    ]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.TextField(verbose_name='배송지')
    state = models.TextField(choices=states)
    number = models.TextField(verbose_name='운송장번호')
    mountain = models.BooleanField(verbose_name='산간지역유무')
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE)
    # todo:
    # refund도


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    receipt_id = models.CharField(max_length=100, verbose_name='영수증키')


class Follow(models.Model):
    _from = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='_from', on_delete=models.CASCADE)
    _to = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='_to', on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, blank=True, null=True, on_delete=models.CASCADE)
    is_follow = models.BooleanField(default=True)