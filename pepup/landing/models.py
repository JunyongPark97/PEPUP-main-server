from django.db import models

# Create your models here.


class Register(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    quantity = models.CharField(max_length=100)
    bank = models.CharField(max_length=100)
    account = models.CharField(max_length=100)
    created_at = models.DateField(auto_now_add=True)