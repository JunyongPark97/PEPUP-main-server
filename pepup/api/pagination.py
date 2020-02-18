from rest_framework.response import Response
from core.pagination import PepupPagination
from collections import OrderedDict


class HomePagination(PepupPagination):
    page_size = 51  # 한페이지에 담기는 개수


class FollowPagination(PepupPagination):
    page_size = 20  # 한페이지에 담기는 개수


class ProductSearchResultPagination(PepupPagination):
    page_size = 30  # 한페이지에 담기는 개수


class TagSearchResultPagination(PepupPagination):
    page_size = 30  # 한페이지에 담기는 개수

    def get_paginated_response(self, data, tag_followed=None):

        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_page_num()),
            ('previous', self.get_prev_page_num()),
            ('tag_followed', tag_followed),
            ('results', data)
        ]))


class StorePagination(PepupPagination):
    page_size = 51

    def get_paginated_response(self, data, profile=None):

        if not profile:
            return Response(OrderedDict([
                ('count', self.page.paginator.count),
                ('next', self.get_next_page_num()),
                ('previous', self.get_prev_page_num()),
                ('results', data)
            ]))
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_page_num()),
            ('previous', self.get_prev_page_num()),
            ('info', profile),
            ('results', data)
        ]))


class StoreReviewPagination(PepupPagination):
    page_size = 15

    def get_paginated_response(self, profile, data=None):

        if not data:
            return Response(OrderedDict([
                ('count', 0),
                ('next', 0),
                ('previous', 0),
                ('info', profile),
                ('results', [])
            ]))
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_page_num()),
            ('previous', self.get_prev_page_num()),
            ('info', profile),
            ('results', data)
        ]))