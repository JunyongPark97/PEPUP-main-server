from django.db import models
from django.contrib.auth.models import (AbstractUser, AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.conf import settings


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, nickname, phone, **kwargs):
        if not email:
            raise ValueError('이메일을 입력해주세요')
        email = self.normalize_email(email)
        user = self.model(email=email, nickname=nickname,phone=phone, **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, nickname, phone, password=None,  **kwargs):
        kwargs.setdefault('is_staff', False)
        kwargs.setdefault('is_superuser',False)
        return self._create_user(email,password,**kwargs)

    def create_superuser(self, email, password, nickname, phone, **kwargs):
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)

        if kwargs.get('is_staff') is not True:
            raise ValueError('superuser must have is_staff=True')
        if kwargs.get('is_superuser') is not True:
            raise ValueError('superuser must have is_superuser=True')
        return self._create_user(email,password, nickname, phone, **kwargs)


class User(AbstractUser):
    username = None
    email = models.EmailField(verbose_name='email address', db_index=True, unique=True, null=True)
    nickname = models.CharField(max_length=30, unique=True, null=True, verbose_name='nickname')
    phone = models.CharField(max_length=19, unique=True, null=True, help_text='숫자만 입력해주세요')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname', 'phone']

    objects = UserManager()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    quit_at = models.DateTimeField(blank=True, null=True, default=None)

    def __str__(self):
        if self.is_anonymous:
            return 'anonymous'
        if self.nickname:
            return self.nickname
        if self.email:
            return self.email
        return self.phone


class PhoneConfirm(models.Model):
    user = models.OneToOneField(User, related_name='phone_confirm',on_delete=models.CASCADE, blank=True, null=True)
    key = models.CharField(max_length=6)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class SmsConfirm(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=6)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    for_email = models.BooleanField(default=False)
    for_password = models.BooleanField(default=False)


def img_directory_path_profile(instance, filename):
    return 'user/{}/profile/{}'.format(instance.user.email, filename)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    thumbnail_img = models.ImageField(upload_to=img_directory_path_profile,
                                      default='default_profile.png', null=True)
    # background_img = models.ImageField(upload_to=img_directory_path_profile, null=True, blank=True)
    introduce = models.TextField(verbose_name='소개', default="")

    @property
    def profile_img_url(self):
        """
        1. thumbnail_img가 자신이 올린 것이 있을 경우
        2. 없으면 socialaccount의 last의 img사용
        3. 없을시 default사용
        """
        if self.thumbnail_img.name != "default_profile.png":
            return self.thumbnail_img.url
        elif hasattr(self.user.socialaccount_set.last(), 'extra_data'):
            if 'properties' in self.user.socialaccount_set.last().extra_data:
                if self.user.socialaccount_set.last().extra_data['properties'].get('profile_image'):
                    self.user.socialaccount_set.last().extra_data['properties'].get('profile_image')
                else:
                    return "http://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/media/default_profile.png"
        else:
            return self.thumbnail_img.url


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, verbose_name='이름', default='')
    zipNo = models.CharField(max_length=10, verbose_name='우편번호')
    Addr = models.TextField(verbose_name='주소')
    phone = models.CharField(max_length=19, verbose_name='전화번호')
    detailAddr = models.TextField(verbose_name='상세주소')
    recent = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class DeliveryPolicy(models.Model):
    seller = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_policy')
    general = models.IntegerField(verbose_name='일반')
    mountain = models.IntegerField(verbose_name='산간지역')
    amount = models.IntegerField(verbose_name='총액조건', default=0)
    active_amount = models.BooleanField(default=False, help_text='배송정책 on off')
    volume = models.IntegerField(verbose_name='총량조건', default=0)
    active_volume = models.BooleanField(default=False, help_text='배송정책 on off')

    def get_delivery_charge(self, amount,volume,mountain=False):
        ret = 0
        if mountain:
            ret += self.mountain
        if amount < self.amount and volume < self.volume:
            ret += self.general
        return ret


class StoreAccount(models.Model):
    BANK = [
        (1, '신한'),
        (2, 'KB국민'),
        (3, '우리'),
        (4, '기업'),
        (5, 'SC제일'),
        (6, '농협'),
        (7, '하나'),
        (8, '외환(하나)'),
        (9, '카카오뱅크'),
        (10, '산업'),
        (11, '씨티'),
        (12, '케이뱅크'),
        (13, '우체국'),
        (14, '새마을'),
        (15, '수협'),
        (16, '신협'),
        (17, '광주'),
        (18, '전북'),
        (19, '부산'),
        (20, '대구'),
        (21, '경남'),
        (22, 'HSBC'),
        (23, 'JP모간'),
        (24, 'BOA'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='account')
    bank = models.IntegerField(choices=BANK)
    account = models.CharField(max_length=100)
    account_holder = models.CharField(max_length=30)
