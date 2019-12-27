from django.db import models
from django.conf import settings

# Create your models here.
class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name='브랜드명')


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='상품명')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    size = models.TextField()
    price = models.IntegerField(verbose_name='가격')
    content = models.TextField(verbose_name='설명')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    thumnail = models.ImageField(upload_to='')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    sold = models.BooleanField(default=False, verbose_name='판매완료')
    promote_rate = models.FloatField(default=0, verbose_name='할인율')
    promotion_price = models.IntegerField(verbose_name='할인가격')

    def __str__(self):
        return self.name

    # sold 후 delete 불가능하게!
    # def lock_delete():


class Promotion(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)


class Payment(models.Model):
    pass


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

class Trade(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='buyer')
    pay_end = models.BooleanField(default=False, verbose_name='결제완료')
    pay_end_date = models.DateTimeField(blank=True, null=True, verbose_name='결제완료시간')
    trade_end = models.BooleanField(default=False, verbose_name='거래완료')
    trade_end_date = models.DateTimeField(blank=True, null=True, verbose_name='거래완료시간')
    payment = models.OneToOneField(Payment, blank=True, null=True, on_delete=models.CASCADE)
    delivery = models.OneToOneField(Delivery,blank=True, null=True, on_delete=models.CASCADE)


class Refund(models.Model):
    trade = models.OneToOneField(Trade, on_delete=models.CASCADE)


