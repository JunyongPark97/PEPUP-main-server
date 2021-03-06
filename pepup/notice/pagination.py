from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from urllib import parse as urlparse
from base64 import b64decode, b64encode
from collections import OrderedDict

from core.pagination import PepupPagination


class PepupCursorPagination(CursorPagination):

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


class NoticePagination(PepupPagination):
    page_size = 15
    ordering = ('-important', '-created_at')

    def get_paginated_response(self, data, banner=None):

        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_page_num()),
            ('previous', self.get_prev_page_num()),
            ('banner', banner),
            ('results', data)
        ]))


class EventNoticePagination(PepupCursorPagination):
    page_size = 15
    ordering = ('-created_at', )

