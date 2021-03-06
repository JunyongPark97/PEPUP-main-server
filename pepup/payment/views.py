from datetime import datetime

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
from user_activity.models import UserActivityLog, UserActivityReference
from .Bootpay import BootpayApi
# model
from accounts.models import User, DeliveryPolicy
from .loader import load_credential
from .models import Payment, Trade, Deal, Delivery, DeliveryMemo, TradeErrorLog, PaymentErrorLog, WalletLog
from payment.models import Commission

# serializer
from .serializers import (
    TradeSerializer,
    PayformSerializer,
    PaymentDoneSerialzier,
    PaymentCancelSerialzier,
    GetPayFormSerializer,
    AddressSerializer, UserNamenPhoneSerializer, DeliveryMemoSerializer)
from .utils import groupbyseller


def pay_test(request):
    return render(request, 'pay_test.html')


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
        return Response({'detail': 'bagging success'}, status=status.HTTP_200_OK)

    # def groupbyseller(self, dict_ls):
    #     ret_ls = []
    #     store = {}
    #     helper = 0
    #     for d in dict_ls:
    #         if d['seller']['id'] in store.keys():
    #             store[d['seller']['id']]['products'] \
    #                 .append({'trade_id': d['id'], 'product': d['product']})
    #             store[d['seller']['id']]['payinfo']['total'] += d['product']['discounted_price']
    #
    #             helper += 1  # ?????? else ?????? ?????? ???????????? ????????? ????????? ???????????? ??? ??????.
    #             if helper == 1:
    #                 store[d['seller']['id']]['payinfo']['lack_amount'] -= d['product']['discounted_price']
    #                 store[d['seller']['id']]['payinfo']['lack_volume'] -= 1
    #
    #             if store[d['seller']['id']]['payinfo']['lack_amount'] > 0:  # ???????????????????????? ?????? ????????? 0????????? ??? ???
    #                 store[d['seller']['id']]['payinfo']['lack_amount'] -= d['product']['discounted_price']
    #             elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0 and d['payinfo']['active_amount']:
    #                 store[d['seller']['id']]['payinfo']['delivery_charge'] = 0
    #
    #             if store[d['seller']['id']]['payinfo']['lack_volume'] > 0:  # ???????????????????????? ?????? ????????? 0????????? ??? ???
    #                 store[d['seller']['id']]['payinfo']['lack_volume'] -= 1
    #             elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0 and d['payinfo']['active_volume']:
    #                 store[d['seller']['id']]['payinfo']['delivery_charge'] = 0
    #
    #         else:
    #             lack_amount = d['payinfo']['amount'] - d['product']['discounted_price']
    #             lack_volume = d['payinfo']['volume'] - 1
    #
    #             if lack_amount <= 0 and d['payinfo']['active_amount']:
    #                 delivery_charge = 0
    #             elif lack_volume <= 0 and d['payinfo']['active_volume']:
    #                 delivery_charge = 0
    #             else:
    #                 delivery_charge = d['payinfo']['general']
    #
    #             store[d['seller']['id']] = {
    #                 'seller': d['seller'],
    #                 'products': [{'trade_id': d['id'], 'product': d['product']}],
    #                 'payinfo': {
    #                     'total': d['product']['discounted_price'],
    #                     'delivery_charge': delivery_charge,
    #                     'active_amount': d['payinfo']['active_amount'],
    #                     'active_volume': d['payinfo']['active_volume'],
    #                     'lack_amount': lack_amount,
    #                     'lack_volume': lack_volume
    #                 }
    #             }
    #     for key in store:
    #         ret_ls.append(store[key])
    #     return ret_ls

    # todo: code, status and serializer data
    # todo: query duplicate fix
    @action(methods=['get'], detail=False, )
    def cart(self, request):
        """
        method: GET
        :param request:
        :return: code, status, and serializer data(trades)
        """
        self.buyer = request.user
        self.trades = Trade.objects \
            .select_related('seller', 'seller__profile') \
            .select_related('seller__delivery_policy') \
            .select_related('product', 'product__size', 'product__size__category', 'product__brand',
                            'product__second_category') \
            .prefetch_related('product__prodthumbnail__product') \
            .filter(buyer=self.buyer, status=1)
        if self.trades.filter(product__sold=True):
            self.trades.filter(product__sold=True).delete()
        serializer = TradeSerializer(self.trades, many=True)
        return Response(groupbyseller(serializer.data))

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
            return Response(status=status.HTTP_400_BAD_REQUEST)  # TODO: how to ???????

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
        ordering_product = groupbyseller(trade_serializer.data)
        total_price = 0
        delivery_charge = 0
        mountain_delivery_charge = 0

        for product in ordering_product:
            payinfo_data = product.copy()
            payinfo = payinfo_data.pop('payinfo')
            total_price = total_price + int(payinfo['total'])
            delivery_charge = delivery_charge + int(payinfo['delivery_charge'])
            mountain_delivery_charge = mountain_delivery_charge + int(payinfo['mountain_delivery_charge'])

        return Response({"ordering_product": ordering_product,
                         "user_info": user_info.data,
                         "address": addr,
                         "memo_list": memo_list,
                         "price": {"total_price": total_price,
                                   "total_delivery_charge": delivery_charge,
                                   "total_mountain_delivery_charge": mountain_delivery_charge,
                                   }
                         })


class PaymentViewSet(viewsets.GenericViewSet):
    queryset = Trade.objects.all().select_related('product', 'product__seller')
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    def check_trades(self):
        """
        1. filter??? trades?????? pk list??? request?????? pk??? ?????? ??? ??????
        """

        if not list(self.trades.values_list('pk', flat=True)) == self.trades_id:
            raise exceptions.NotAcceptable(detail='????????? trade??? ????????? ?????????, ????????? ????????? ?????????????????????.')

    def check_sold(self):
        sold_products_trades = self.trades.filter(product__sold=True)
        user = self.request.user
        product_ids = Product.objects.filter(trade__in=self.trades, sold=True)
        if sold_products_trades:
            sold_products_trades.delete()  # ?????? ????????? ????????????, ??????(trades)?????? ???????????????.
            TradeErrorLog.objects.create(user=user, product_ids=list(product_ids), status=1, description="sold ??? ????????? ??????")
            raise exceptions.NotAcceptable(detail='????????? ????????? ???????????? ????????????.')

    def create_payment(self):
        self.payment = Payment.objects.create(user=self.request.user)

    def get_deal_total_and_delivery_charge(self, seller, trades):
        """
        :param seller:
        :param trades:
        :return: (total, remain, delivery_charge)
        """
        commission_rate = Commission.objects.last().rate  # admin?????? ??????

        total_discounted_price = trades.aggregate(
            total_discounted_price=Sum(
                Ceil((F('product__price') * (1 - F('product__discount_rate'))) / 100) * 100,
                output_field=IntegerField()
            )
        )['total_discounted_price']
        if self.serializer.data['mountain']:  # client ?????? ???????????? On ?????? ???.
            delivery_charge = seller.delivery_policy.mountain
        else:
            volume = trades.count()
            if volume > seller.delivery_policy.volume and seller.delivery_policy.active_volume:
                delivery_charge = 0
            elif total_discounted_price > seller.delivery_policy.amount and seller.delivery_policy.active_amount:
                delivery_charge = 0
            else:
                delivery_charge = seller.delivery_policy.general  # ????????? ?????? ??????.

        return (
            total_discounted_price + delivery_charge,
            total_discounted_price * (1 - commission_rate) + delivery_charge,
            # reamin : ???????????? ??? ???. ???????????? ????????? ???????????? ???????????? ?????? ???????????? ??????.
            delivery_charge
        )

    def create_deals(self):
        bulk_list_delivery = []
        for seller_id in self.trades.values_list('seller', flat=True).distinct():  # ?????? ?????? ????????? ????????? ??? ?????????.
            trades_groupby_seller = self.trades.filter(seller_id=seller_id)  # ?????? ?????? ??????.
            seller = trades_groupby_seller.first().seller  # ?????? ???????????? ????????????.
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
                deal=deal  # ????????? ?????????(??? ?????? ????????? ????????? ?????? ????????? ????????? delivery??????), ?????? ?????? ??????.
            ))
            trades_groupby_seller.update(deal=deal)
        # payment??? price
        # for ?????? ????????? ????????? payment??? total(????????? ???????????? ????????? ??????)??? ???????????? ????????? ????????? ????????? ??????(?????? ???????????? ???????????? ????????? ?????????: group_by_seller)
        # ?????? ?????? ?????? : ?????? ?????? ????????? ????????? ?????????.
        ## ?????? payment ???????????? ??????. ????????????.
        total_sum = self.payment.deal_set.aggregate(total_sum=Sum('total'))['total_sum']
        if not total_sum == int(self.request.data.get('price')):
            raise exceptions.NotAcceptable(detail='????????? ?????????????????? ????????????.')
        self.payment.price = total_sum

        if self.trades.count() > 1:
            self.payment.name = self.trades.first().product.name + ' ??? ' + str(self.trades.count() - 1) + '???'
        else:
            self.payment.name = self.trades.first().product.name
        self.payment.save()
        Delivery.objects.bulk_create(bulk_list_delivery)

    @action(methods=['post'], detail=False, serializer_class=GetPayFormSerializer)
    def get_payform(self, request):
        """
        method: POST
        :param request: trades, price, address, memo, mountain, application_id
        :return: result {payform}
        """
        self.request = request

        data = request.data.copy()
        # replace type for web debugging, TODO : remove here
        price = data.pop('price')
        address = data.pop('address')
        memo = data.pop('memo')
        application_id = data.pop('application_id')
        trades = data.pop('trades')
        mountain = data.pop('mountain')
        trades_list = []

        if type(trades[0]) == str:
            for trade in trades:
                trades_list.append(int(trade))
        else:
            trades_list = trades

        trades_list.sort()

        price = int(price[0]) if type(price) == list else price
        address = address[0] if type(address) == list else address
        memo = memo[0] if type(memo) == list else memo
        application_id = application_id[0] if type(application_id) == list else application_id
        val_data = {'trades': trades_list, 'price': price, 'address': address, 'memo': memo,
                    'application_id': application_id, 'mountain': mountain}

        self.serializer = self.get_serializer(data=val_data)
        if not self.serializer.is_valid():
            raise exceptions.NotAcceptable(detail='request body is not validated')
        self.trades_id = trades_list
        self.trades = self.get_queryset() \
            .select_related('product') \
            .select_related('seller', 'seller__delivery_policy') \
            .filter(pk__in=self.trades_id, buyer=request.user)
        self.check_trades()
        self.check_sold()

        # todo: transaction atomic ???????????? , ???????????? payment??? ?????? ?????????.
        # todo: payment??? ???????????? ??????!!!
        with transaction.atomic():
            self.create_payment()
            self.create_deals()

        items = self.trades

        serializer = PayformSerializer(self.payment, context={
            'addr': address,
            'application_id': int(application_id),
            'items': items
        })

        return Response({'results': serializer.data}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def confirm(self, request):
        """
        method: POST
        :param request: order_id, receipt_id(?????? ???????????? ?????? ??????:pg ??? ??????)
        :return: code and status
        """
        payment = Payment.objects.get(pk=request.data.get('order_id'))
        user = request.user

        if Product.objects.filter(trade__deal__payment=payment, sold=True):
            # ????????? ????????? ???????????????, user??? trades, deal, delivery, payment??? ???????????????
            deals = payment.deal_set.all()
            for deal in deals:
                deal.trade_set.all().delete()
                deal.delivery.delete()
            deals.delete()
            payment.delete()
            product_ids = Product.objects.filter(trade__deal__payment=payment, sold=True).values_list('id', flat=True)
            TradeErrorLog.objects.create(user=user, product_ids=list(product_ids), status=2, description="sold ??? ????????? ??????")
            raise exceptions.NotAcceptable(detail='????????? ????????? ???????????? ????????????.')

        payment.receipt_id = request.data.get('receipt_id')
        payment.save()

        # deal : ?????? ??????
        payment.deal_set.all().update(status=12)

        return Response(status=status.HTTP_200_OK)

    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"),
                             private_key=load_credential("private_key"))
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay
        else:
            raise exceptions.APIException(detail='bootpay access token ????????????')

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
        try:
            payment = Payment.objects.get(id=order_id)
        except Payment.DoesNotExist:
            # ?????? ????????? ????????????, payment ??? ?????? ????????????, User??? ????????? ????????? payment??? ???????????? ?????? ?????? ??????
            PaymentErrorLog.objects.create(user=request.user, temp_payment=request.user.payment_set.last())
            raise exceptions.NotFound(detail='?????? order_id??? payment??? ???????????? ????????????.')

        # todo: receipt_id??? order_id??? payment??? ??? ?????? ??? payment??? trades??? status??? ????????? ???????????? ??????
        # todo: front?????? ????????? ?????? ????????? ????????? ?????? ?????????,
        # todo: https://docs.bootpay.co.kr/deep/submit ?????? ????????? ?????? ??????????????? ?????????????????? ?????? ????????? ??????
        # todo: https://github.com/bootpay/server_python/blob/master/lib/BootpayApi.py ??? ??????
        if not (receipt_id or order_id):
            raise exceptions.NotAcceptable(detail='request body is not validated')

        # ?????? ?????? ??? (?????????????????? ?????? ????????????, done ?????? ?????? ???)
        payment.status = 3
        payment.save()

        # deal : bootpay ?????? ??????
        payment.deal_set.all().update(status=13)

        buyer = payment.user

        bootpay = self.get_access_token()
        result = bootpay.verify(receipt_id)
        if result['status'] == 200:
            # ??????!
            if payment.price == result['data']['price']:
                serializer = PaymentDoneSerialzier(payment, data=result['data'])
                if serializer.is_valid():
                    serializer.save()
                    # ?????? ?????? sold??????
                    products = Product.objects.filter(trade__deal__payment=payment)
                    products.update(sold=True, sold_status=1)
                    # ?????? trade 2????????? : ????????????
                    trades = Trade.objects.filter(deal__payment=payment)
                    trades.update(status=2)
                    # deal : ????????????, ?????? ?????? ??????
                    payment.deal_set.update(status=2, transaction_completed_date=datetime.now())
                    # walletlog ?????? : ????????? walletlog??? ???????????? ??????
                    for deal in payment.deal_set.all():
                        WalletLog.objects.create(deal=deal, user=deal.seller)

                        reference = UserActivityReference.objects.create(deal=deal)
                        # activity log ?????? : seller
                        UserActivityLog.objects.create(user=deal.seller, status=200, reference=reference)
                        # activity log ?????? : buyer
                        UserActivityLog.objects.create(user=buyer, status=100, reference=reference)
                    return Response(status.HTTP_200_OK)
        else:
            result = bootpay.cancel('receipt_id')
            serializer = PaymentCancelSerialzier(payment, data=result['data'])
            if serializer.is_valid():
                serializer.save()
                # trade : bootpay ?????? ??????
                Trade.objects.filter(deal__payment=payment).update(status=-3) #?????????????????? ??????????????? ??????.
                # deal : bootpay ?????? ??????
                payment.deal_set.all().update(status=-3)

                # activity log : buyer ?????? ?????????
                UserActivityLog.objects.create(user=buyer, status=190)

                return Response({'detail': 'canceled'}, status=status.HTTP_200_OK)

        # todo: http stateless ????????? ????????? ????????? ?????? ?????? ?????? ????????? ?????????????????????????????? ????????? ???...
        return Response({'detail': ''}, status=status.HTTP_200_OK)

    def error(self, request):
        pass


class PayInfo(APIView):
    # todo : ????????? ?????? ????????? ???????????? 25????????? ???????????? ??? ???????????? ?????? ?????? ????????? ??? ??????
    # todo : private_key ????????? ??? ???????????? ????????? ??????
    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"),
                             private_key=load_credential("private_key"))
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
    # todo: ???????????? ?????? ????????? ??? ?????????
    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"),
                             private_key=load_credential("private_key"))
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    def post(self, request, format=None, **kwargs):
        bootpay = self.get_access_token()
        receipt_id = request.META.get('HTTP_RECEIPTID')
        refund = request.data
        print(refund)
        cancel_result = bootpay.cancel(receipt_id, refund['name']['amount'], refund['name']['name'],
                                       refund['name']['description'])
        if cancel_result['status'] is 200:
            return JsonResponse(cancel_result)
        else:
            return JsonResponse(cancel_result)
