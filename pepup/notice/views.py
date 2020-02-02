from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from notice.models import Notice, FAQ, Official
from notice.pagination import NoticePagination
from notice.serializers import NoticeSerializer, FAQSerializer, OfficialSerializer


class NoticeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    pagination_class = NoticePagination

    def get_queryset(self):
        queryset = self.queryset
        if self.action == 'list':
            queryset = queryset.filter(hidden=False)
        return queryset.order_by('-important', '-created_at')

    def list(self, request, *args, **kwargs):
        """
        공지사항 list API입니다.
        """
        return super(NoticeViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        공지사항 상세 API입니다.
        """
        return super(NoticeViewSet, self).retrieve(request, *args, **kwargs)


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer

    def list(self, request, *args, **kwargs):
        """
        FAQ list API입니다.
        """
        # filter
        filter_param = int(request.query_params.get('filter', 1))

        if filter_param == 2:
            # 앱 기능 관련
            queryset = self.get_queryset().filter(group=2)
        elif filter_param == 3:
            # 앱 오류 관련
            queryset = self.get_queryset().filter(group=3)
        elif filter_param == 4:
            # 주문,배송 관련
            queryset = self.get_queryset().filter(group=4)
        elif filter_param == 5:
            # 환불 관련
            queryset = self.get_queryset().filter(group=5)
        elif filter_param == 6:
            # 기타
            queryset = self.get_queryset().filter(group=10)
        else:
            queryset = self.get_queryset()

        # 전체
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """
        FAQ 상세 API입니다.
        """
        return super(FAQViewSet, self).retrieve(request, *args, **kwargs)


class OfficialViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Official.objects.all()
    serializer_class = OfficialSerializer

    @action(detail=False, methods=['GET'], url_path='use-terms')
    def use_terms(self, request):
        obj = self.get_queryset().filter(official_type=0).order_by('version').last()
        serializer = self.get_serializer(obj)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='privacy-policy')
    def privacy_policy(self, request):
        obj = self.get_queryset().filter(official_type=1).order_by('version').last()
        serializer = self.get_serializer(obj)

        return Response(serializer.data, status=status.HTTP_200_OK)