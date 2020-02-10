from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response
from urllib import parse as urlparse
from base64 import b64decode, b64encode
from collections import OrderedDict


def _reverse_ordering(ordering_tuple):
    """
    Given an order_by tuple such as `('-created', 'uuid')` reverse the
    ordering and return a new tuple, eg. `('created', '-uuid')`.
    """

    def invert(x):
        return x[1:] if x.startswith('-') else '-' + x

    return tuple([invert(item) for item in ordering_tuple])


class PepupPagination(PageNumberPagination):
    page_size = 50  # 한페이지에 담기는 개수

    def get_next_page_num(self):
        if not self.page.has_next():
            return None
        page_number = self.page.next_page_number()
        return page_number

    def get_prev_page_num(self):
        if not self.page.has_previous():
            return None
        page_number = self.page.previous_page_number()
        return page_number

    def get_paginated_response(self, data):
        return Response(OrderedDict([
             ('count', self.page.paginator.count),
             ('next', self.get_next_page_num()),
             ('previous', self.get_prev_page_num()),
             ('results', data)
         ]))


class PepupCursorPagination(CursorPagination):
    # page_size = ...
    # ordering = ...

    def get_paginated_response(self, data):
        response = Response(data)
        response['cursor-prev'] = self.get_previous_link()
        response['cursor-next'] = self.get_next_link()
        return response

    def encode_cursor(self, cursor):
        """
        Given a Cursor instance, return an url with encoded cursor.
        """
        tokens = {}
        if cursor.offset != 0:
            tokens['o'] = str(cursor.offset)
        if cursor.reverse:
            tokens['r'] = '1'
        if cursor.position is not None:
            tokens['p'] = cursor.position

        querystring = urlparse.urlencode(tokens, doseq=True)
        encoded = b64encode(querystring.encode('ascii')).decode('ascii')
        return encoded


def paginate(page_size=None, ordering=None):

    class _Pagination(PepupCursorPagination):
        def __init__(self):
            self.page_size = page_size
            self.ordering = ordering

    def decorator(_class):
        _class.pagination_class = _Pagination
        return _class

    return decorator
