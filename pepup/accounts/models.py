from django.db import models
from django.contrib.auth.models import (AbstractUser, AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.conf import settings

from api.models import Payment


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
    email = models.EmailField(verbose_name='email address', unique=True)
    nickname = models.CharField(max_length=30, unique=True, null=True, verbose_name='nickname')
    phone = models.CharField(max_length=19, unique=True, null=True, help_text='숫자만 입력해주세요')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname', 'phone']

    objects = UserManager()

    def __str__(self):
        if self.nickname:
            return self.nickname
        return self.email


class PhoneConfirm(models.Model):
    user = models.OneToOneField(User, related_name='phone_confirm',on_delete=models.CASCADE, blank=True, null=True)
    key = models.CharField(max_length=6)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


def img_directory_path_profile(instance, filename):
    return 'user/{}/profile/{}'.format(instance.user.email, filename)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    thumbnail_img = models.ImageField(upload_to=img_directory_path_profile)
    background_img = models.ImageField(upload_to=img_directory_path_profile)
    address1 = models.TextField(verbose_name='주소1')
    address2 = models.TextField(verbose_name='주소2')
    introduce = models.TextField(verbose_name='소개')


class DeliveryPolicy(models.Model):
    seller = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_policy')
    general = models.IntegerField(verbose_name='일반')
    mountain = models.IntegerField(verbose_name='산간지역')
    amount = models.IntegerField(verbose_name='총액조건')
    volume = models.IntegerField(verbose_name='총량조건')

    def get_delivery_charge(self, amount,volume,mountain=False):
        ret = 0
        if mountain:
            ret += self.mountain
        if amount < self.amount and volume < self.volume:
            ret += self.general
        return ret


class WalletLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.IntegerField()
    log = models.TextField(verbose_name='로그')
    payment = models.ForeignKey(Payment, blank=True, null=True, on_delete=models.CASCADE)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)