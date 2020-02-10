from rest_framework import pagination
from rest_framework.response import Response
from core.pagination import PepupPagination


class HomePagination(PepupPagination):
    page_size = 51  # 한페이지에 담기는 개수


class FollowPagination(PepupPagination):
    page_size = 20  # 한페이지에 담기는 개수