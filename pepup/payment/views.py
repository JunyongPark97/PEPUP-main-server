from django.shortcuts import render
import json
import uuid

import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, mixins
from rest_framework.decorators import authentication_classes, action
from rest_framework import status, viewsets
from rest_framework import exceptions

from django.db.models import F, Sum, Count, ExpressionWrapper
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.db.models import Q as q
from django.db import transaction
from django.db.models import IntegerField, Value, Case, When
from django.db.models.functions import Ceil

from api.models import Product
from .Bootpay import BootpayApi
# model
from accounts.models import User, DeliveryPolicy
from .loader import load_credential
from .models import Payment, Trade, Deal, Delivery, DeliveryMemo
from payment.models import Commission

# serializer
from .serializers import (
    TradeSerializer,
    PayformSerializer,
    PaymentDoneSerialzier,
    PaymentCancelSerialzier,
    GetPayFormSerializer,
    AddressSerializer, UserNamenPhoneSerializer, DeliveryMemoSerializer)



def pay_test(request):
    return render(request,'pay_test.html')


# Cart
class TradeViewSet(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=['get'], detail=True)
    def bagging(self, request, pk):
        """
        method: GET
        :param request: check header ->
        :param pk:
        :return:
            okay : status 200
            notfound : status 404
        """
        buyer = request.user
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            raise exceptions.NotFound()
        Trade.objects.get_or_create(
            product=product,
            seller=product.seller,
            buyer=buyer,
        )
        return Response({'detail': 'bagging success'},status=status.HTTP_200_OK)

    def groupbyseller(self, dict_ls):
        ret_ls = []
        store = {}
        helper = 0
        for d in dict_ls:
            if d['seller']['id'] in store.keys():
                store[d['seller']['id']]['products']\
                    .append({'trade_id': d['id'], 'product': d['product']})
                store[d['seller']['id']]['payinfo']['total'] += d['product']['discounted_price']

                helper += 1  # 한번 else 부터 갔다 들어오기 때문에 첫번째 들어왔을 때 뺴줌.
                if helper == 1:
                    store[d['seller']['id']]['payinfo']['lack_amount'] -= d['product']['discounted_price']
                    store[d['seller']['id']]['payinfo']['lack_volume'] -= 1

                if store[d['seller']['id']]['payinfo']['lack_amount'] > 0: # 가격할인정책에서 남은 가격이 0원보다 클 때
                    store[d['seller']['id']]['payinfo']['lack_amount'] -= d['product']['discounted_price']
                elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0 and d['payinfo']['active_amount']:
                    store[d['seller']['id']]['payinfo']['delivery_charge'] = 0

                if store[d['seller']['id']]['payinfo']['lack_volume'] > 0: # 수량할인정책에서 남은 개수가 0개보다 클 때
                    store[d['seller']['id']]['payinfo']['lack_volume'] -= 1
                elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0 and d['payinfo']['active_volume']:
                    store[d['seller']['id']]['payinfo']['delivery_charge'] = 0

            else:
                lack_amount = d['payinfo']['amount'] - d['product']['discounted_price']
                lack_volume = d['payinfo']['volume'] - 1

                if lack_amount <= 0 and d['payinfo']['active_amount']:
                    delivery_charge = 0
                elif lack_volume <= 0 and d['payinfo']['active_volume']:
                    delivery_charge = 0
                else:
                    delivery_charge = d['payinfo']['general']

                store[d['seller']['id']] = {
                    'seller': d['seller'],
                    'products': [{'trade_id': d['id'], 'product': d['product']}],
                    'payinfo': {
                        'total': d['product']['discounted_price'],
                        'delivery_charge': delivery_charge,
                        'active_amount': d['payinfo']['active_amount'],
                        'active_volume': d['payinfo']['active_volume'],
                        'lack_amount': lack_amount,
                        'lack_volume': lack_volume
                    }
                }
        for key in store:
            ret_ls.append(store[key])
        return ret_ls

    # todo: code, status and serializer data
    # todo: query duplicate fix
    @action(methods=['get'], detail=False,)
    def cart(self, request):
        """
        method: GET
        :param request:
        :return: code, status, and serializer data(trades)
        """
        self.buyer = request.user
        self.trades = Trade.objects\
            .select_related('seller', 'seller__profile')\
            .select_related('seller__delivery_policy')\
            .select_related('product', 'product__size', 'product__size__category', 'product__brand', 'product__second_category')\
            .prefetch_related('product__prodthumbnail_set__product')\
            .filter(buyer=self.buyer, status=1)
        if self.trades.filter(product__sold=True):
            self.trades.filter(product__sold=True).delete()
        serializer = TradeSerializer(self.trades, many=True)
        return Response(self.groupbyseller(serializer.data))

    @action(methods=['post'], detail=False)
    def cancel(self, request):
        """
        method: POST
        :param request: trades list(by pk)
        :return: code and status
        """
        ls_cancel = request.data['trades']
        trades = Trade.objects.filter(pk__in=ls_cancel, status=1)
        if trades:
            trades.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False)
    def payform(self, request, *args, **kwargs):
        user = request.user

        trades_id = request.data['trades']
        trades = Trade.objects.filter(pk__in=trades_id, buyer=user, status=1)

        # delete sold trades
        if trades.filter(product__sold=True):
            trades.filter(product__sold=True).delete()
            return Response(status=status.HTTP_400_BAD_REQUEST) # TODO: how to 깔끔?

        if not trades:
            return Response(status=status.HTTP_204_NO_CONTENT)

        user_info = UserNamenPhoneSerializer(user)
        addresses = user.address_set.filter(recent=True)

        if addresses:
            addr = AddressSerializer(addresses.last()).data
        else:
            addr = None

        memos = DeliveryMemo.objects.filter(is_active=True).order_by('order')
        memo_list = DeliveryMemoSerializer(memos, many=True).data

        trade_serializer = TradeSerializer(trades, many=True)
        ordering_product = self.groupbyseller(trade_serializer.data)
        total_price = 0
        delivery_charge = 0
        for product in ordering_product:
            payinfo = product.pop('payinfo')
            total_price = total_price + int(payinfo['total'])
            delivery_charge = delivery_charge + int(payinfo['delivery_charge'])
        return Response({"ordering_product": ordering_product,
                         "user_info": user_info.data,
                         "address": addr,
                         "memo_list": memo_list,
                         "price": {"total_price": total_price, "total_delivery_charge": delivery_charge}
                         })


class PaymentViewSet(viewsets.GenericViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    def check_trades(self):
        """
        1. filter된 trades들의 pk list가 request받은 pk와 같은 지 확인
        """
        if not list(self.trades.values_list('pk', flat=True)) == self.trades_id:
            raise exceptions.NotAcceptable(detail='요청한 trade의 정보가 없거나, 잘못된 유저로 요청하였습니다.')

    def check_sold(self):
        sold_products = self.trades.filter(product__sold=True)
        if sold_products:
            sold_products.delete() # 만약 결제된 상품이면, 카트(trades)에서 삭제해야함.
            raise exceptions.NotAcceptable(detail='판매된 상품이 포함되어 있습니다.')

    def create_payment(self):
        self.payment = Payment.objects.create(user=self.request.user)

    def get_deal_total_and_delivery_charge(self, seller, trades):
        """
        :param seller:
        :param trades:
        :return: (total, remain, delivery_charge)
        """
        commission_rate = Commission.objects.last().rate # admin에서 처리

        total_discounted_price = trades.aggregate(
            total_discounted_price=Sum(
                Ceil((F('product__price') * (1 - F('product__discount_rate'))) / 100) * 100,
                output_field=IntegerField()
            )
        )['total_discounted_price']

        if self.serializer.data['mountain']: # client 에서 도서산간 On 했을 때.
            delivery_charge = seller.delivery_policy.mountain
        else:
            volume = trades.count()
            if volume < seller.delivery_policy.volume and total_discounted_price < seller.delivery_policy.amount:
                delivery_charge = seller.delivery_policy.general
            else:
                delivery_charge = 0 # 배송비 할인.

        return (
            total_discounted_price + delivery_charge,
            total_discounted_price * (1 - commission_rate) + delivery_charge, # reamin : 셀러한테 줄 값. 배송비는 결제시 우리한테 결제하고 추후 셀러한테 지급.
            delivery_charge
        )

    def create_deals(self):
        bulk_list_delivery = []
        for seller_id in self.trades.values_list('seller', flat=True).distinct(): # 서로 다른 셀러들 결제시 한 셀러씩.
            trades_groupby_seller = self.trades.filter(seller_id=seller_id) # 셀러 별로 묶기.
            seller = trades_groupby_seller.first().seller # 셀러 인스턴스 가져오기.
            total, remain, delivery_charge = self.get_deal_total_and_delivery_charge(seller, trades_groupby_seller)
            deal = Deal.objects.create(
                buyer=self.request.user,
                seller=seller,
                total=total,
                remain=remain,
                delivery_charge=delivery_charge,
                payment=self.payment
            )
            bulk_list_delivery.append(Delivery(
                sender=seller,
                receiver=self.request.user,
                address=self.serializer.data['address'],
                memo=self.serializer.data['memo'],
                mountain=self.serializer.data['mountain'],
                state='step0',
                deal=deal # 유저가 결제시(한 셀러 샵에서 여러개 상품 구매시 하나의 delivery생성), 배송 정보 기입.
            ))
            trades_groupby_seller.update(deal=deal)
        # payment의 price
        # for 문이 끝나고 생성된 payment의 total(할인된 가격이면 할인된 가격)을 계산해서 유저가 요청한 금액과 비교(유저 카트에서 계산해서 할인가 띄워줌: group_by_seller)
        # 에러 나는 경우 : 구매 중에 셀러가 할인가 적용시.
        ## 아직 payment 부르지도 않음. 검증과정.
        total_sum = self.payment.deal_set.aggregate(total_sum=Sum('total'))['total_sum']
        if not total_sum == int(self.request.data.get('price')):
            raise exceptions.NotAcceptable(detail='가격을 확인해주시길 바랍니다.')
        self.payment.price = total_sum
        if self.payment.deal_set.count() > 1:
            self.payment.name = self.trades.first().product.name + ' 외 ' + str(self.payment.deal_set.count()-1) + '건'
        else:
            self.payment.name = self.trades.first().product.name
        self.payment.save()
        Delivery.objects.bulk_create(bulk_list_delivery)

    @transaction.atomic
    @action(methods=['post'], detail=False, serializer_class=GetPayFormSerializer)
    def get_payform(self, request):
        """
        method: POST
        :param request: trades, price, address, memo, mountain, application_id
        :return: result {payform}
        """
        self.request = request
        self.serializer = self.get_serializer(data=request.data)
        if not self.serializer.is_valid():
            raise exceptions.NotAcceptable(detail='request body is not validated')
        self.trades_id = list(map(int, request.data.getlist('trades')))
        self.trades = self.get_queryset()\
            .select_related('product')\
            .select_related('seller', 'seller__delivery_policy')\
            .filter(pk__in=self.trades_id, buyer=request.user)

        self.check_trades()
        self.check_sold()

        # todo: transaction atomic 시작부분 , 안묶으면 payment는 계속 생성됨.
        # todo: payment는 삭제하면 안됨!!!
        with transaction.atomic():
            self.create_payment()
            self.create_deals()

        serializer = PayformSerializer(self.payment, context={
            'addr': request.data.get('address'),
            'application_id': request.data.get('application_id')
        })
        return Response({'results': {'payform':serializer.data, 'payment_id':self.payment.id}}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def confirm(self, request):
        """
        method: POST
        :param request: order_id, receipt_id(결제 영수증과 같은 개념:pg 사 발행)
        :return: code and status
        """
        payment = Payment.objects.get(pk=request.data.get('order_id'))
        payment.receipt_id = request.data.get('receipt_id')
        payment.save()
        if Product.objects.filter(trade__deal__payment=payment, sold=True):
            raise exceptions.NotAcceptable(detail='판매된 제품이 포함되어 있습니다.')
        return Response(status=status.HTTP_200_OK)

    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"), private_key=load_credential("private_key"))
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay
        else:
            raise exceptions.APIException(detail='bootpay access token 확인바람')

    @transaction.atomic
    @action(methods=['post'], detail=False)
    def done(self, request):
        """
        method: POST
        :param request: order_id, receipt_d
        :return: status, code
        """
        receipt_id = request.data.get('receipt_id')
        order_id = request.data.get('order_id')

        # todo: receipt_id와 order_id로 payment를 못 찾을 시 payment와 trades의 status를 조정할 알고리즘 필요
        # todo: front에서 제대로 값만 잘주면 문제될 것은 없지만,
        # todo: https://docs.bootpay.co.kr/deep/submit 해당 링크를 보고 서버사이드 결제승인으로 바꿀 필요성 있음
        # todo: https://github.com/bootpay/server_python/blob/master/lib/BootpayApi.py 맨 밑줄
        if not (receipt_id or order_id):
            raise exceptions.NotAcceptable(detail='request body is not validated')
        try:
            payment = Payment.objects.get(id=order_id)
        except Payment.DoesNotExist:
            raise exceptions.NotFound(detail='해당 order_id의 payment가 존재하지 않습니다.')

        bootpay = self.get_access_token()
        result = bootpay.verify(receipt_id)
        if result['status'] == 200:
            if payment.price == result['data']['price']:
                serializer = PaymentDoneSerialzier(payment, data=result['data'])
                if serializer.is_valid():
                    serializer.save()
                    # 관련 상품 sold처리
                    products = Product.objects.filter(trade__deal__payment=payment)
                    products.update(sold=True)
                    # 하위 trade 2번처리 : 결제완료
                    trades = Trade.objects.filter(deal__payment=payment)
                    trades.update(status=2)
                    return Response(status.HTTP_200_OK)
        else:
            result = bootpay.cancel('receipt_id')
            serializer = PaymentCancelSerialzier(payment, data=result['data'])
            if serializer.is_valid():
                serializer.save()
                Trade.objects.filter(deal__payment=payment).update(status=-3)
                return Response({'detail': 'canceled'}, status=status.HTTP_200_OK)

        # todo: http stateless 특성상 데이터 집계가 될수 없을 수도 있어서 서버사이드랜더링으로 고쳐야 함...
        return Response({'detail': ''}, status=status.HTTP_200_OK)

    def error(self, request):
        pass


class PayInfo(APIView):
    # todo : 최적화 필요 토큰을 저장하고 25분마다 생성하고 그 안에서는 있는 토큰 사용할 수 있게
    # todo : private_key 초기화 및 가져오는 처리도 필요
    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"), private_key=load_credential("private_key"))
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    @authentication_classes(authentication.TokenAuthentication)
    def get(self, request, format=None):
        bootpay = self.get_access_token()
        receipt_id = request.META.get('HTTP_RECEIPTID')
        info_result = bootpay.verify(receipt_id)
        if info_result['status'] is 200:
            return JsonResponse(info_result)

    @authentication_classes(authentication.TokenAuthentication)
    def post(self, request):
        bootpay = self.get_access_token()
        receipt_id = request.META.get('HTTP_RECEIPTID')
        info_result = bootpay.verify(receipt_id)
        if info_result['status'] is 200:
            all_fields = Payment.__dict__.keys()
            filtered_dict = {}
            for key in info_result['data']:
                if key in all_fields:
                    filtered_dict[key] = info_result['data'][key]
            payment = Payment.objects.create(**filtered_dict)
            print(payment)
            serializer = PaymentSerializer(payment)
            serializer.save()
            return JsonResponse(serializer.data)
        else:
            return JsonResponse(info_result)


class RefundInfo(APIView):
    # todo: 부트페이 계정 초기화 및 일반화
    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"), private_key=load_credential("private_key"))
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    def post(self, request, format=None, **kwargs):
        bootpay = self.get_access_token()
        receipt_id = request.META.get('HTTP_RECEIPTID')
        refund = request.data
        print(refund)
        cancel_result = bootpay.cancel(receipt_id, refund['name']['amount'], refund['name']['name'], refund['name']['description'])
        if cancel_result['status'] is 200:
            return JsonResponse(cancel_result)
        else:
            return JsonResponse(cancel_result)