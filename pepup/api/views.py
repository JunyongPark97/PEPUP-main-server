import json

import requests
from django.db import transaction
from django.db.models.functions import Coalesce
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, mixins
from rest_framework.decorators import authentication_classes, action
from rest_framework import status, viewsets, generics
from rest_framework import exceptions

from django.db.models import F, Sum, Q, Value as V, Count, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.db.models import Q as q
from django.db import transaction
from django.db.models import IntegerField, Value, Case, When, Prefetch
from .loader import load_credential
from django.contrib.auth import logout
# model
from accounts.models import User, Profile
from .models import (Product, ProdThumbnail, Payment,
                     Brand, Trade, Like, Follow,
                     Tag, Deal, Delivery, FirstCategory, SecondCategory, Size, GenderDivision)


# serializer
from .serializers import (
    ProductSerializer,
    TradeSerializer,
    BrandSerializer,
    MainSerializer,
    LikeSerializer,
    FollowSerializer,
    PayFormSerializer,
    SearchResultSerializer, DeliveryPolicySerializer, RelatedProductSerializer, FollowingSerializer,
    StoreProductSerializer, StoreSerializer, StoreLikeSerializer, FirstCategorySerializer, SecondCategorySerializer,
    GenderSerializer, TagSerializer, SizeSerializer, ProductCreateSerializer)

from accounts.serializers import UserSerializer

from api.pagination import FollowPagination, HomePagination, ProductSearchResultPagination, \
    TagSearchResultPagination, StorePagination

# bootpay
from .Bootpay import BootpayApi

# utils
from accounts.utils import get_user, get_follower


def pay_test(request):
    return render(request,'pay_test.html')


class ProductViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.all()
    pagination_class = HomePagination
    permission_classes = [IsAuthenticated, ]

    def get_serializer_class(self):
        serializer = ProductSerializer
        if self.action == 'list':
            serializer = MainSerializer
        elif self.action == 'create':
            serializer = ProductCreateSerializer
        return serializer

    def list(self, request):
        """
        :method: GET
        :param request:
        :return:
        """
        try:
            products = self.queryset\
                .select_related('seller__profile')\
                .prefetch_related('seller___to') \
                .prefetch_related(Prefetch('seller__product_set', queryset=self.queryset.filter(sold=True)))\
                .prefetch_related('seller__product_set__seller').prefetch_related('prodthumbnail_set').all()
        except Product.DoesNotExist:
            raise Http404

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset=products, request=request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def set_prodThumbnail(self, product, request):
        for thum in request.FILES.getlist('thums'):
            ProdThumbnail.objects.create(
                product=product,
                thumbnail=thum
            )

    @transaction.atomic
    def create(self, request):
        """
        :method: POST
        :param request:
        :return: code and status
        """

        data = request.data.copy()

        if not 'image' in data:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        image_data = data.pop('image')

        if '' in image_data:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        tags = data.pop('tag')

        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            data = serializer.validated_data
            data.update({'images': image_data})
            product = serializer.create(data)

            for tag_value in tags:
                tag, _ = Tag.objects.get_or_create(tag=tag_value)
                product.tag.add(tag.id)

            return Response(status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # TODO : TO BE CHANGE SERVER NAME
    def request_classification(self, images):
        server_url = ""
        request_options = [
            {
                'version': 1,
                'use_cache': True,
            }
        ]

        data = {
            'image_url': images,
            'requests': request_options,
        }

        try:
            result = json.loads(requests.post(  # Request / Post method
                server_url,
                json=data).text)

        except:
            result = None

        return result[0]


    @action(methods=['get'], detail=True)
    def search(self, request, pk):
        """
        [DEPRECATED] -> SearchViewSet
        """
        query = q(name__icontains=pk)
        products = Product.objects.filter(query)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializers = ProductSerializer(products, many=True)
        return Response(serializers.data)

    def retrieve(self, request, pk, format=None):
        """
        :method: GET
        :param request:
        :param pk:
        :param format:
        :return:
        """
        user = request.user
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        try:
            like = Like.objects.get(user=user, product=product)
            is_liked = like.is_liked
        except Like.DoesNotExist:
            is_liked = False
        is_bagged = Trade.objects.filter(product=product, buyer=user)
        if is_bagged.exists():
            bagged = True
        else:
            bagged = False

        serializer = ProductSerializer(product)
        delivery_policy = DeliveryPolicySerializer(product.seller.delivery_policy)

        related_products = self.get_related_products(product)
        if related_products:
            related_products = RelatedProductSerializer(related_products, many=True).data
        else:
            related_products = None
        return Response({
            'product': serializer.data,
            'isbagged': bagged,
            'liked': is_liked,
            'delivery_policy': delivery_policy.data,
            'related_products': related_products
        })

    # TODO : filter by second category
    def get_related_products(self, product):
        second_category = product.second_category
        tags = product.tag.all()
        filtered_products = Product.objects\
            .select_related('size','size__category','size__category__gender')\
            .prefetch_related('tag').\
            exclude(id=product.id).\
            annotate(count=Count(
                Case(
                    When(
                        tag__id__in=list(tag.id for tag in tags), then=1),
                    output_field=IntegerField(),
                )
            )
        ).distinct().order_by('-count')[:5]

        return filtered_products


    # todo: response fix -> code and status
    @action(methods=['post'], detail=True, serializer_class=LikeSerializer)
    def like(self, request, pk):
        """
        method: POST
        :param request:
        :param pk:
        :return: code, status
        """
        user = request.user
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'status': 'Product does not exist'}, status=status.HTTP_404_NOT_FOUND)
        like, tf = Like.objects.get_or_create(user=user, product=product)
        if not tf:
            if like.is_liked:
                like.is_liked = False
            else:
                like.is_liked = True
            like.save()
        serializer = self.get_serializer(like)
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True, serializer_class=LikeSerializer)
    def liked(self, request, pk):
        """
        :method: GET
        :param request:
        :param pk:
        :return: cod and status
        """
        user = request.user
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'status': 'product does not exist'},status=status.HTTP_404_NOT_FOUND)
        try:
            like = Like.objects.get(user=user, product=product)
        except Like.DoesNotExist:
            return Response({'returns': {'is_liked':False}}, status=status.HTTP_200_OK)
        return Response({'returns': self.get_serializer(like).data}, status.HTTP_200_OK)

    def update(self, request, pk=None):
        pass

    def partial_update(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass


class ProductCategoryAPIViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):
        queryset = FirstCategory.objects.filter(is_active=True)
        if self.action == 'gender':
            queryset = GenderDivision.objects.filter(is_active=True)
        elif self.action == 'second_category':
            queryset = SecondCategory.objects.filter(is_active=True)
        elif self.action == 'size':
            queryset = Size.objects.all()
        elif self.action == 'brand':
            queryset = Brand.objects.all()
        return queryset

    def get_serializer_class(self):
        serializer = FirstCategorySerializer
        if self.action == 'gender':
            serializer = GenderSerializer
        elif self.action == 'second_category':
            serializer = SecondCategorySerializer
        elif self.action == 'size':
            serializer = SizeSerializer
        elif self.action == 'brand':
            serializer = BrandSerializer
        return serializer

    @action(methods=['get'], detail=False,)
    def gender(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=True)
    def first_category(self, request, *args, **kwargs):
        gender_pk = kwargs['pk']
        try:
            gender = GenderDivision.objects.get(pk=gender_pk)
        except GenderDivision.DoesNotExist:
            raise Http404
        queryset = self.get_queryset().filter(gender=gender)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=True)
    def second_category(self, request, *args, **kwargs):
        fc_pk = kwargs['pk']
        try:
            first_category = FirstCategory.objects.get(pk=fc_pk)
        except FirstCategory.DoesNotExist:
            raise Http404
        queryset = self.get_queryset().filter(parent=first_category)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=True)
    def size(self, request, *args, **kwargs):
        fc_pk = kwargs['pk']
        try:
            first_category = FirstCategory.objects.get(pk=fc_pk)
        except FirstCategory.DoesNotExist:
            raise Http404
        queryset = self.get_queryset().filter(category=first_category)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def brand(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TagViewSet(viewsets.GenericViewSet):
    queryset = Tag
    permission_classes = [IsAuthenticated,]

    @action(methods=['post'], detail=False)
    def searching(self, request, *args, **kwargs):
        """
        tag page 에서 tag 검색을 할 때 각 글자에 해당하는 태그를 조회하는 api 입니다.
        없는 태그의 경우 create 를 TagViewSet에서 하지 않고 ProductViewSet의 create 에서 생성됩니다.
        """
        keyword = request.data['keyword']
        queryset = Tag.objects.prefetch_related('product_set') \
                              .filter(tag__icontains=keyword) \
                              .annotate(product_count=Count('product')) \
                              .values('tag', 'id') \
                              .order_by('-product_count')[:15]
        if not queryset.exists():
            return None
        serializer = TagSerializer(queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FollowViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = FollowSerializer
    pagination_class = FollowPagination
    permission_classes = [IsAuthenticated]

    def get_recommended_seller(self):
        self.recommended_seller = User.objects.all()
        if self.recommended_seller.count() > 10:
            self.recommended_seller = self.recommended_seller[:10]
        # todo: recommend query
        ########
        # todo: serializer 최적화
        self.recommended = UserSerializer(self.recommended_seller, many=True)

    def get_products_by_follow(self):
        follows = Follow.objects.filter(_from=self.user)
        self.follows_by_seller = follows.filter(tag=None)
        self.follows_by_tag = follows\
            .prefetch_related('tag')\
            .filter(_to=None)
        self.products_by_seller = Product.objects\
            .select_related('seller', 'brand')\
            .select_related('seller__profile')\
            .prefetch_related('seller___to')\
            .prefetch_related('tag')\
            .filter(seller___to__in=self.follows_by_seller)\
            .annotate(by=Value(1, output_field=IntegerField()))
        self.products_by_tag = Product.objects\
            .select_related('brand', 'category', 'category__parent') \
            .select_related('seller__profile') \
            .prefetch_related('seller___to') \
            .prefetch_related('tag')\
            .filter(tag__follow__in=self.follows_by_tag) \
            .annotate(by=Value(2, output_field=IntegerField()))

    def custom_get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'].update(self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    # todo: response -> code, status and paginated response
    def list(self, request):
        """
        :method: GET
        :param request: header token
        :return: code, status and paginated response
        """
        self.user = request.user
        if self.user.is_anonymous:
            return Response({'code': -1, 'status': "로그인해주세요"})
        self.get_products_by_follow()
        self.get_recommended_seller()
        print(list(self.products_by_seller.values_list('id', flat=True)))
        page = self.paginate_queryset(self.products_by_seller | self.products_by_tag)
        if page is not None:
            serializer = self.custom_get_serializer(page, many=True, context={"request": self.request, "by_seller": list(self.products_by_seller.values_list('id', flat=True))})
            return self.get_paginated_response({
                "products": serializer.data,
                "recommended": self.recommended.data
            })
        serializer = MainSerializer(self.products_by_tag|self.products_by_seller, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False, serializer_class=FollowingSerializer)
    def check_follow(self, request):
        """
        :method: POST
        :param request:
        :return: results or status
        """
        _from = request.user
        _to = request.data.get('_to')
        tag = request.data.get('tag')

        if _to:
            try:
                follow = Follow.objects.get(_from=_from, _to_id=_to)
            except Follow.DoesNotExist:
                return Response({'returns': {'is_follow': False}}, status=status.HTTP_200_OK)
        elif tag:
            try:
                follow = Follow.objects.get(_from=_from, tag_id=tag)
            except Follow.DoesNotExist:
                return Response({'returns': {'is_follow': False}}, status=status.HTTP_200_OK)
        else:
            return Response({'status': '요청바디가 없습니다.'},status=status.HTTP_400_BAD_REQUEST)
        return Response({'returns': {'is_follow': follow.is_follow}}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, serializer_class=FollowingSerializer)
    def following(self, request):
        """
        :method: POST
        :param request:
        :return: results or status
        """
        _from = request.user
        _to = request.data.get('_to')
        tag = request.data.get('tag')
        if _to:
            if _from.pk == int(_to):
                return Response({'status': "user can't follow himself"}, status=status.HTTP_406_NOT_ACCEPTABLE)
            try:
                _to = User.objects.get(pk=_to)
                follow, created = Follow.objects.get_or_create(_from=_from, _to=_to)
            except User.DoesNotExist:
                return Response({'status': "_to does not exist"}, status=status.HTTP_404_NOT_FOUND)
        elif tag:
            try:
                tag = Tag.objects.get(pk=tag)
                follow, created = Follow.objects.get_or_create(_from=_from, tag_id=tag)
            except Tag.DoesNotExist:
                return Response({'status': "Tag does not exist"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'status': '요청바디가 없습니다.'},status=status.HTTP_400_BAD_REQUEST)
        if not created:
            if follow.is_follow:
                follow.is_follow = False
            else:
                follow.is_follow = True
            follow.save()
        return Response({'results': self.get_serializer(follow).data}, status=status.HTTP_200_OK)


# Cart
class TradeViewSet(viewsets.GenericViewSet):
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
        for d in dict_ls:
            if d['seller']['id'] in store.keys():
                store[d['seller']['id']]['products']\
                    .append({'trade_id': d['id'], 'product': d['product']})
                store[d['seller']['id']]['payinfo']['total'] += d['product']['discounted_price']
                if store[d['seller']['id']]['payinfo']['lack_amount'] > 0:
                    store[d['seller']['id']]['payinfo']['lack_amount'] -= d['product']['discounted_price']
                elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0:
                    store[d['seller']['id']]['payinfo']['delivery_charge'] = 0
                if store[d['seller']['id']]['payinfo']['lack_volume'] > 0:
                    store[d['seller']['id']]['payinfo']['lack_volume'] -= 1
                elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0:
                    store[d['seller']['id']]['payinfo']['delivery_charge'] = 0
            else:
                lack_amount = d['payinfo']['amount'] - d['product']['discounted_price']
                lack_volume = d['payinfo']['volume'] - 1
                if lack_amount <= 0 or lack_volume <= 0:
                    delivery_charge = 0
                else:
                    delivery_charge = d['payinfo']['general']
                store[d['seller']['id']] = {
                    'seller': d['seller'],
                    'products': [{'trade_id': d['id'], 'product': d['product']}],
                    'payinfo': {
                        'total': d['product']['discounted_price'],
                        'delivery_charge': delivery_charge,
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
            .select_related('product', 'product__size', 'product__size__category', 'product__brand', 'product__second_category')\
            .prefetch_related('product__prodthumbnail_set__product')\
            .filter(buyer=self.buyer, status=1)
        if self.trades.filter(product__sold=True):
            self.trades.filter(product__sold=True).delete()
        serializer = TradeSerializer(self.trades, many=True)
        return Response(self.groupbyseller(serializer.data))

    # todo: code, status and serializer data
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
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)

from api.serializers import GetPayFormSerializer

class PaymentViewSet(viewsets.GenericViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"), private_key=load_credential("private_key"))
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    def check_trades(self):
        """
        1. filter된 trades들의 pk list가 request받은 pk와 같은 지 확인
        2. sold 되었는지 확인
        """

        if not list(self.trades.values_list('pk', flat=True)) == self.request.data.get('trades'):
            raise exceptions.NotAcceptable(detail='요청한 trade의 정보가 없거나, 잘못된 유저로 요청하였습니다.')

        sold_products = self.trades.filter(product__sold=True)
        if sold_products:
            sold_products.delete()
            raise exceptions.NotAcceptable(detail='판매된 상품입니다.')

    def create_payment(self):
        self.payment = Payment.objects.create(user=self.request.user)
        self.deals.update(payment=self.payment)

    def create_deals(self):
        bulk_list_deals = []
        bulk_list_delivery = []
        for seller_id in self.trades.values_list('seller', flat=True).distinct():
            trades_groupby_seller = self.trades.filter(seller_id=seller_id)
            seller = trades_groupby_seller.first().seller
            delivery = Delivery(
                sender=seller,
                receiver=self.request.user,
                address=self.request.data.get('address'),
                memo=self.request.data.get('memo'),
                mountain=self.request.data.get('mountain'),
                state='step1'
            )
            bulk_list_delivery.append(delivery)
            total = 10000
            delivery_charge = 2500
            bulk_list_deals.append(Deal(
                buyer=self.request.user,
                seller=seller,
                total=total,
                remain=total,
                delivery=delivery,
                delivery_charge=delivery_charge
            ))
        Delivery.objects.bulk_create(bulk_list_delivery)
        self.deals = Deal.objects.bulk_create(bulk_list_deals)

    @transaction.atomic
    @action(methods=['post'], detail=False, serializer_class=GetPayFormSerializer)
    def get_payform(self, request):
        """
        method: POST
        :param request: price, trade list,
        :return: code, status and result
        """
        self.request = request
        self.trades = self.get_queryset()\
            .select_related('product')\
            .select_related('seller', 'seller__delivery_policy')\
            .filter(pk__in=request.data.get('trades'), buyer=request.user)
        self.check_trades()
        self.create_deals()
        self.create_payment()
        return Response({})

    @action(methods=['post'], detail=False)
    def confirm(self, request):
        """
        method: POST
        :param request:
        :return: code and status
        """
        return

    @action(methods=['post'], detail=False)
    def done(self, request):
        """
        method: POST
        :param request:
        :return: status, code
        """
        return

    def canceled(self, request):
        pass

    def error(self, request):
        pass

    # def is_valid_products(self):
    #     solded_products = self.products.filter(sold=True)
    #     if solded_products:
    #         self.trades.filter(product__in=solded_products).delete()
    #         self.response = Response({'code': -1, 'result': '재고가 없습니다.'})
    #         return False
    #     return True
    #
    # def create_payment(self):
    #     self.payment = Payment.objects.create(
    #         status=0,
    #         user=self.user,
    #     )
    #
    # def update_payment(self):
    #     self.payment = Payment.objects.get(order_id=self.request.data['order_id'])
    #     bootpay = self.get_access_token()
    #     receipt_id = self.request.data['receipt_id']
    #     info_result = bootpay.verify(receipt_id)
    #     if info_result['status'] is 200:
    #         info_result['data']
    #
    # def _get_payform(self):
    #     self.trades = Trade.objects.filter(pk__in=self.request.data.getlist('trades'))
    #     if len(self.trades) == 0:
    #         self.response = Response({'code': -2, 'result': "데이터가 없습니다."},status=status.HTTP_404_NOT_FOUND)
    #         return False
    #     if len(self.trades) == 1:
    #         self.name = self.trades[0].product.name
    #     else:
    #         self.name = self.trades[0].product.name + ' 외 ' + str(len(self.trades) - 1) + '건'
    #     self.products = Product.objects.filter(trade__in=self.trades)
    #     self.create_payment()
    #     self.payform = PayFormSerializer(
    #         data=self.request.data,
    #         context={'name': self.name,
    #                  'products': self.products,
    #                  'user': self.user,
    #                  'order_id': self.payment.order_id}
    #     )
    #     return True
    #
    # @action(methods=['post'], detail=False)
    # def get_payform(self, request):
    #     """
    #     method: POST
    #     :param request:
    #     :return: code, status and result
    #     """
    #     self.request = request
    #     self.user = request.user
    #     if not self._get_payform():
    #         return self.response    # set self.payform
    #     if not self.is_valid_products():
    #         return self.response
    #     if self.payform.is_valid():
    #         return Response({'code': 1, 'result': self.payform.data})
    #     return Response(self.payform.errors)
    #
    # def set_address(self):
    #     if hasattr(self.request.data, 'address'):
    #         self.address = self.request.data['address']
    #     else:
    #         self.address = get_object_or_404(Profile, user=self.user).address1
    #
    # def create_delivery(self, seller):
    #     self.delivery = Delivery.objects.create(
    #         sender=seller,
    #         receiver=self.user,
    #         address=self.address,
    #         state='STEP0',
    #         number=None,
    #         mountain=self.request.data['mountain']
    #     )
    #
    # def link_deal(self):
    #     for deal in self.request.data.getlist('deal'):  # 1 item = 1 deal
    #         self.create_delivery(deal['seller'])
    #         self.deal = Deal.objects.create(
    #             seller=deal['seller'],
    #             buyer=self.user,
    #             payment=self.payment,
    #             total=deal['total'],
    #             remain=deal['total'],
    #             delivery=self.delivery
    #         )
    #         # link deal to payment, and trades to deal
    #         self.payment.deal_set.add(deal)
    #         for trade in self.deal['trades']:
    #             trade = Trade.objects.get(pk=trade)
    #             self.deal.trade_set.add(trade)
    #
    # @action(methods=['post'], detail=False)
    # def confirm(self, request):
    #     """
    #     method: POST
    #     :param request:
    #     :return: code and status
    #     """
    #     self.products = Product.objects.filter(pk__in=request.data.getlist('products'))
    #     if not self.is_valid_products():
    #         self.create_payment()
    #         return self.response
    #     return Response({"code": -1}, status=status.HTTP_200_OK)
    #
    # @action(methods=['post'], detail=False)
    # def done(self, request):
    #     """
    #     method: POST
    #     :param request:
    #     :return: status, code
    #     """
    #     # request = {receipt_id, address, deal:[{seller, trades, total, delivery_charge}]}
    #     self.request = request
    #     self.user = get_user(self.request)
    #     self.set_address()
    #     self.update_payment()
    #     self.link_deal()
    #
    #     trades = Trade.objects.filter(pk__in=request.data.getlist('trades'))
    #     products = Product.objects.filter(trades__in=trades)
    #     if self.is_valid_products():
    #         products.update(sold=True)
    #         trades.update(status=2)
    #         return Response({"code": 3}, status=status.HTTP_200_OK)
    #     return Response({"code": -1}, status=status.HTTP_200_OK)
    #
    # def canceled(self, request):
    #     pass
    #
    # def error(self, request):
    #     pass


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


class SearchViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = SearchResultSerializer

    @action(methods=['post'],detail=False)
    def searching(self, request):
        """
        :methods: POST
        :param request:
        :return:
        """
        keyword = request.data['keyword']
        if len(keyword) < 1:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        product_count = self.search_by_product(keyword)
        tags = self.search_by_tag(keyword)
        seller_qs = UserSerializer(self.search_by_seller(keyword), many=True)
        searched_data = {}
        searched_data['name_result'] = product_count
        searched_data['tag_result'] = tags
        searched_data['seller_result'] = seller_qs.data
        return Response(searched_data)

    @action(methods=['post'], detail=False)
    def product_search(self, request):
        """
        product name 이 포함된 products 상품을 return 합니다.
        :method: POST
        :param request: keyword (string) 검색 하는 값
        :return: paginated data, status
        """
        keyword = request.data['keyword']
        if len(keyword) < 1:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            products = Product.objects.filter(name__icontains=keyword).order_by('-created_at')
        except Product.DoesNotExist:
            raise Http404

        paginator = ProductSearchResultPagination()
        page = paginator.paginate_queryset(products, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['get'], detail=True)
    def tag_search(self, request, pk):
        """
        searching api 에서 주어졌던 tag_id 기반으로 상품을 return 합니다.
        :method: GET
        :param request:
        :return: paginated data, tag_followed: bool, status
        """
        # get user
        user = request.user

        # get tag
        try:
            tag = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            raise Http404

        # get tag followed
        try:
            tag_followed = Follow.objects.get(tag=tag, _from=user).is_follow
        except:
            tag_followed = False

        paginator = TagSearchResultPagination()
        products = Product.objects.filter(tag=tag).order_by('-created_at')
        page = paginator.paginate_queryset(queryset=products, request=request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data, tag_followed=tag_followed)

    def search_by_product(self, keyword):
        searched_product = Product.objects.filter(name__icontains=keyword)
        return searched_product.count()

    # TODO : recommend by user logs(searched, clicked, liked, followed), optimize
    def search_by_tag(self, keyword):
        queryset_values = Tag.objects.prefetch_related('product_set')\
            .filter(tag__icontains=keyword)\
            .annotate(product_count=Count('product'))\
            .values('tag', 'id')\
            .order_by('-product_count')[:5]
        return queryset_values

    # TODO : ordering by related seller (Seller product's tag), optimize
    def search_by_seller(self, keyword):
        queryset = User.objects.prefetch_related('product_set')\
            .filter(nickname__icontains=keyword)\
            .order_by('nickname')[:5]
        return queryset


class StoreViewSet(viewsets.GenericViewSet):
    pagination_class = StorePagination
    permission_classes = [IsAuthenticated, ]

    @action(methods=['get'], detail=True)
    def shop(self, request, *args, **kwargs):

        retrieve_user = self.get_retrieve_user(kwargs['pk'])

        store_serializer = StoreSerializer(retrieve_user)

        products = retrieve_user.product_set.all().order_by('-created_at')

        paginator = StorePagination()
        page = paginator.paginate_queryset(queryset=products, request=request)
        products_serializer = StoreProductSerializer(page, many=True)

        return paginator.get_paginated_response(products_serializer.data, profile=store_serializer.data)

    @action(methods=['get'], detail=True)
    def liked(self, request, *args, **kwargs):

        retrieve_user = self.get_retrieve_user(kwargs['pk'])
        if not retrieve_user:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        # if not retrieve_user.liker.all():
        #     return Response({}, status=status.HTTP_204_NO_CONTENT)

        # TODO : order by created_at
        likes = retrieve_user.liker.filter(is_liked=True)

        paginator = StorePagination()
        page = paginator.paginate_queryset(queryset=likes, request=request)
        products_serializer = StoreLikeSerializer(page, many=True)
        return paginator.get_paginated_response(products_serializer.data)

    def get_retrieve_user(self, pk):

        try:
            retrieve_user = User.objects.get(pk=pk)
        except:
            retrieve_user = None

        return retrieve_user
