from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator



class Commission(models.Model):
    rate = models.FloatField(verbose_name='수수료', validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    info = models.TextField(verbose_name='내용')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)