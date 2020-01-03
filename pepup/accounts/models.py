from django.db import models
from django.contrib.auth.models import (AbstractUser, AbstractBaseUser, BaseUserManager, PermissionsMixin)


# Create your models here.
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
    nickname = models.CharField(max_length=30, unique=True, verbose_name='nickname')
    phone = models.CharField(max_length=19, unique=True, help_text='숫자만 입력해주세요')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname', 'phone']

    objects = UserManager()

    def __str__(self):
        return self.email


class PhoneConfirm(models.Model):
    user = models.OneToOneField(User, related_name='phone_confirm',on_delete=models.CASCADE)
    key = models.CharField(max_length=6)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

