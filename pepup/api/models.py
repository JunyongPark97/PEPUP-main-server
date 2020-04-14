import os
import urllib
from io import BytesIO

import requests
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.conf import settings
import math
from core.fields import S3ImageKeyField
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
import urllib.request
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
    SOLD_STATUS = [
        (1, 'by payment'),
        (2, 'by user')
    ]

    name = models.CharField(max_length=100, verbose_name='상품명')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name='product', null=True)
    price = models.IntegerField(verbose_name='가격')
    content = models.TextField(verbose_name='설명')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    sold = models.BooleanField(default=False, verbose_name='판매완료')
    sold_status = models.IntegerField(choices=SOLD_STATUS, null=True, blank=True)
    on_discount = models.BooleanField(default=False, verbose_name='세일중')
    discount_rate = models.FloatField(default=0, verbose_name='할인율')
    first_category = models.ForeignKey(FirstCategory, on_delete=models.CASCADE, null=True)
    second_category = models.ForeignKey(SecondCategory, on_delete=models.CASCADE, null=True)
    is_refundable = models.BooleanField(default=False)
    tag = models.ManyToManyField(Tag)
    is_active = models.BooleanField(default=True)

    # todo:
    # 환불가능, 사이즈(카테고리화: 남자->XL),
    # TODO : 판매완료(sold)시 할인율 수정하면 안됨! (정산시 꼬임) => 할인 상품 고르는 api에서 sold로 거르고, admin page
    # TODO : 에서 수정 불가하게 바꿔야함.

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
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    # image_key = S3ImageKeyField() # client key 저장 후 save 시 image 저장
    thumbnail = ProcessedImageField(
        upload_to=thumb_directory_path,  # 저장 위치
        processors=[ResizeToFill(350, 350)],  # 사이즈 조정
        format='JPEG',  # 최종 저장 포맷
        options={'quality': 90},
        null=True, blank=True)

    @property
    def image_url(self):
        return self.thumbnail.url

    def save(self, *args, **kwargs):
        super(ProdThumbnail, self).save(*args, **kwargs)
        self._save_thumbnail()

    def _save_thumbnail(self):
        from PIL import Image
        resp = requests.get(self.product.images.first().image_url)
        image = Image.open(BytesIO(resp.content))
        crop_io = BytesIO()
        crop_io.seek(0)
        # image.convert("RGB")
        image.save(crop_io, format='png')
        crop_file = InMemoryUploadedFile(crop_io, None, self._get_file_name(), 'image/jpeg', len(crop_io.getvalue()), None)
        self.thumbnail.save(self._get_file_name(), crop_file, save=False)
        # To avoid recursive save, call super.save
        super(ProdThumbnail, self).save()

    def _get_file_name(self):
        return '{}.jpg'.format(self.product.images.first().image_key)


class ProdImage(models.Model):
    """
    [DEPRECATED]
    """
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    image = models.FileField(upload_to=img_directory_path)


class ProdS3Image(models.Model):
    """
    s3 presigned post key save
    """
    # TODO : if client can upload, alternate ProdS3Image <-> ProdImage
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images')
    image_key = S3ImageKeyField()

    @property
    def image_url(self):
        return self.image_key.url


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='liker', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    is_liked = models.BooleanField(default=True)


class Follow(models.Model):
    _from = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='_from',
                              on_delete=models.CASCADE)
    _to = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='_to',
                            on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, blank=True, null=True, on_delete=models.CASCADE)
    is_follow = models.BooleanField(default=True)
