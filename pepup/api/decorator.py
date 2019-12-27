from rest_framework.response import Response
from rest_framework import authentication, permissions
from accounts.models import User


def is_user(func):
    def wrapper(*args, **kwargs):
        authentication_classes = [authentication.TokenAuthentication]
        return func(*args, **kwargs)
    return wrapper