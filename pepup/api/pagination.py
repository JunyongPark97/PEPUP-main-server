from rest_framework import pagination
from rest_framework.response import Response


class FollowPagination(pagination.PageNumberPagination):
    def get_paginated_response(self, data, recommended=None):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'results': data,
            'recommended': recommended
        })

class CustomPagination(pagination.PageNumberPagination):
    # def previous_page_number(self):

    def get_paginated_response(self, data, recommended=None):
        return Response({
            'links': {
                'next': self.page.next_page_number(),
                'previous': self.page.previous_page_number()
            },
            'count': self.page.paginator.count,
            'results': data,
            'recommended': recommended
        })
