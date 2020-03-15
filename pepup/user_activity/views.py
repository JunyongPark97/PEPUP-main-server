import os

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets

from django.db.models import Count
from django.db.models.functions import TruncDate
from payment.models import Deal, Review
from payment.serializers import TradeSerializer, UserNamenPhoneSerializer, AddressSerializer
from payment.utils import groupbyseller
from user_activity.serializers import PurchasedDealSerializer, ReviewSerializer, ReviewRetrieveSerializer, \
    SimpleWaybillSerializer


class PurchasedViewSet(viewsets.ModelViewSet):
    serializer_class = PurchasedDealSerializer
    permission_classes = [IsAuthenticated, ]
    queryset = Deal.objects.all().prefetch_related('trade_set', 'trade_set__product', 'trade_set__product__prodthumbnail')\
                                 .select_related('review')

    def list(self, request, *args, **kwargs):
        """
        quseyset status in [2,3,4,5,6] <- 수정하면 안돼요
        수정시 serialzier 의 status 가 바뀔 수 있으니 주의해주세요
        """
        user = request.user
        queryset = self.get_queryset().filter(buyer=user).filter(status__in=[2, 3, 4, 5, 6])\
                                      .filter(transaction_completed_date__isnull=False)
        dates = queryset.annotate(date=TruncDate('transaction_completed_date'))\
            .values('date').annotate(c=Count('id')).order_by()
        # list_data = []
        group_by_date = {}
        for date in dates:
            date = date['date']
            group_by_date_qs = queryset.annotate(date=TruncDate('transaction_completed_date')).filter(date=date)
            serialized_data = self.get_serializer(group_by_date_qs, many=True)
            group_by_date[str(date)] = serialized_data.data
            # group_by_date['date']= str(date)
            # group_by_date['data']= serialized_data.data
            # list_data.append(group_by_date)

        return Response(group_by_date, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        deal = self.get_object()
        user = request.user

        if deal.buyer != user:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        trades = deal.trade_set.all()
        trade_serializer = TradeSerializer(trades, many=True)
        data = groupbyseller(trade_serializer.data)[0]
        data.pop('payinfo')

        # ordered product info
        ordering_product = data

        # user info
        user_info = UserNamenPhoneSerializer(user).data

        # address
        addresses = user.address_set.filter(recent=True)
        if addresses:
            addr = AddressSerializer(addresses.last()).data
        else:
            addr = None

        # pay info : price, delivery_charge, total
        price = 0
        for trade in trades:
            dis_price = trade.product.discounted_price
            price += dis_price
        delivery_charge = deal.delivery_charge
        total = deal.total

        # waybill info
        delivery = deal.delivery
        if delivery.code and delivery.number:
            waybill = SimpleWaybillSerializer(delivery).data
        else:
            waybill = None

        condition = self.get_condition(deal)

        return Response({"ordering_product": ordering_product,
                         "condition": condition,
                         "user_info": user_info,
                         "pay_info":
                             {"price": price, "delivery_charge": delivery_charge, "total": total},
                         "address": addr,
                         "waybill": waybill})

    def get_condition(self, obj):
        status = obj.status
        if status in [13, 2, 3, 4]: # review 작성 전 or 운송장 입력일로부터 5일 이내
            # 수령확인 버튼
            return 0
        elif status in [5, 6]:
            # 리뷰작성 버튼(수령확인은 되었지만(클릭 or 5일자동), 리뷰 글이 없거나 자동수령이 되어 리뷰 자체가 없는 경우)
            if hasattr(obj, 'review'):
                # 리뷰는 있지만, 내용이 없는 경우 : 별점만 준 경우 (수령확인 시)
                if not obj.review.context:
                    return 1 # 리뷰작성
                return 2 # None : 수령확인시 리뷰를 작성했거나, 리뷰작성 버튼을 눌러 리뷰 글이 있는 경우
            else:
                return 1 # 리뷰작성: 자동 수령확인이 되어 리뷰 자체가 없는 경우
        return 3 # 기타

    @action(methods=['post'], detail=True)
    def leave_review(self, request, *args, **kwargs):
        data = request.data.copy()
        deal = self.get_object()

        # get data
        seller = deal.seller
        data.update({'seller': seller.id})
        data.update({'deal': deal.id})

        # update
        if hasattr(deal, 'review'):
            serializer = ReviewSerializer(deal.review, data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            deal.status = 5
            deal.save()
            return Response(status=status.HTTP_206_PARTIAL_CONTENT)

        serializer = ReviewSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # deal status = 5 -> 거래 완료 처리 : 정산 가능
        deal.status = 5
        deal.save()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=['get'], detail=True)
    def review(self, request, *args, **kwargs):
        deal = self.get_object()

        # review 가 없는 경우, 대표이미지와 별점 0점을 default 로 return
        if not hasattr(deal, 'review'):
            url = deal.trade_set.first().product.prodthumbnail.image_url
            return Response({'deal_thumbnail': url, "satisfaction": float(0)}, status=status.HTTP_200_OK)

        review = deal.review
        serializer = ReviewRetrieveSerializer(review)
        return Response(serializer.data, status=status.HTTP_200_OK)
