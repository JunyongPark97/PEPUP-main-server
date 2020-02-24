from django.db import models
from django.conf import settings
# Create your models here.


class Room(models.Model):
    user = models.ManyToManyField(settings.AUTH_USER_MODEL)


class Message(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)


# def message_img_directory_path(instance, filename):
#     return 'user/{}/message_img/{}'.format(instance.message.user.email, filename)
#
#
# class ImageinMessage(models.Model):
#     message = models.ForeignKey(Message, on_delete=models.CASCADE)
#     image = models.FileField(upload_to=message_img_directory_path)