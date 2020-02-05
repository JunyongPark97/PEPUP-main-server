from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from urllib import parse as urlparse
from base64 import b64decode, b64encode


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

    class _Pagination(MondeCursorPagination):
        def __init__(self):
            self.page_size = page_size
            self.ordering = ordering

    def decorator(_class):
        _class.pagination_class = _Pagination
        return _class

    return decorator
