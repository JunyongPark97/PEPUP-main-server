from django.db.models.functions import Coalesce
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import authentication_classes, action
from rest_framework import status, viewsets, generics
from rest_framework.authtoken.models import Token
from rest_framework import mixins
from rest_framework import pagination
from django.db.models import F, Sum, Q, Value as V, Count, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.db.models import Q as q
from django.db.models import Prefetch
from django.db.models import IntegerField, Value, Case, When
from .loader import load_credential
from django.contrib.auth import logout
# model
from accounts.models import User, Profile
from .models import (Product, ProdThumbnail, Payment,
                     Brand, Trade,Like,Follow,
                     Tag, Deal, Delivery)

# serializer
from .serializers import (
    ProductSerializer,
    TradeSerializer,
    BrandSerializer,
    MainSerializer,
    LikeSerializer,
    FollowSerializer,
    PayFormSerializer,
    SearchResultSerializer, DeliveryPolicySerializer, RelatedProductSerializer,FollowingSerializer)

from accounts.serializers import UserSerializer

from api.pagination import FollowPagination, HomePagination, ProductSearchResultPagination, \
    TagSearchResultPagination

# bootpay
from .Bootpay import BootpayApi

# utils
from accounts.utils import get_user, get_follower


def pay_test(request):
    return render(request,'pay_test.html')


class ProductViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = HomePagination

    def list(self, request):
        """
        :method: GET
        :param request:
        :return:
        """
        self.serializer_class = MainSerializer
        try:
            products = self.queryset\
                .select_related('seller__profile')\
                .prefetch_related('seller___to') \
                .prefetch_related(Prefetch('seller__product_set', queryset=self.queryset.filter(sold=True)))\
                .prefetch_related('seller__product_set__seller').prefetch_related('prodthumbnail_set').all()
        except Product.DoesNotExist:
            raise Http404
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page,many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MainSerializer(products, many=True)
        return Response(serializer.data)

    def set_prodThumbnail(self, product, request):
        for thum in request.FILES.getlist('thums'):
            ProdThumbnail.objects.create(
                product=product,
                thumbnail=thum
            )

    def create(self, request):
        """
        :method: POST
        :param request:
        :return: code and status
        """
        seller = get_user(request)
        brand = get_object_or_404(Brand, id=int(request.POST['brand_id']))
        serializer = ProductSerializer(data=request.data,partial=True)
        if serializer.is_valid():
            product = serializer.save(
                seller=seller,
                brand=brand
            )
            self.set_prodThumbnail(product, request)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True)
    def search(self, request, pk):
        """
        [DEPRECATED] -> SearchViewSet
        :method: GET
        :param request:
        :param pk:
        :return: code, status, paginated response
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
            like = Like.objects.get(user=user, product=product,is_liked=False)
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
        print(related_products)
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
            # 'seller': {
            #     'id': product.seller.id,
            #     'reviews': 0,
            #     'sold': len(sold_products),
            #     'follower': len(follower),
            # },
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
            .select_related('seller', 'category', 'brand')\
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

    @action(methods=['get'], detail=True)
    def bagging(self, request, pk):
        """
        method: GET
        :param request: check header ->
        :param pk:
        :return:
        """
        buyer = request.user
        product = get_object_or_404(Product,pk=pk)
        Trade.objects.get_or_create(
            product=product,
            seller=product.seller,
            buyer=buyer,
        )
        return Response(status=status.HTTP_200_OK)

    def groupbyseller(self, dict_ls):
        ret_ls = []
        store = {}
        for d in dict_ls:
            if d['seller']['id'] in store.keys():
                store[d['seller']['id']]['products'].append({'trade_id':d['id'],'product':d['product']})
            else:
                store[d['seller']['id']] = {'seller': d['seller'],'products': [{'trade_id': d['id'], 'product': d['product']}]}
        for key in store:
            ret_ls.append(store[key])
        return ret_ls

    # todo: code, status and serializer data
    # todo: query duplicate fix
    @action(methods=['get'], detail=False)
    def cart(self, request):
        """
        method: GET
        :param request:
        :return: code, status, and serializer data(trades)
        """
        if request.user.is_anonymous:
            return Response({'status': '로그인이 되지 않았습니다.'},status=status.HTTP_401_UNAUTHORIZED)
        self.buyer = request.user
        self.trades = Trade.objects.filter(buyer=self.buyer)
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
        trades = Trade.objects.filter(pk__in=ls_cancel)
        if trades:
            trades.delete()
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)


class PaymentViewSet(viewsets.GenericViewSet):
    def get_access_token(self):
        bootpay = BootpayApi(application_id=load_credential("application_id"), private_key=load_credential("private_key"))
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    def is_valid_products(self):
        solded_products = self.products.filter(sold=True)
        if solded_products:
            self.trades.filter(product__in=solded_products).delete()
            self.response = Response({'code': -1, 'result': '재고가 없습니다.'})
            return False
        return True

    def create_payment(self):
        self.payment = Payment.objects.create(
            status=0,
            user=self.user,
        )

    def update_payment(self):
        self.payment = Payment.objects.get(order_id=self.request.data['order_id'])
        bootpay = self.get_access_token()
        receipt_id = self.request.data['receipt_id']
        info_result = bootpay.verify(receipt_id)
        if info_result['status'] is 200:
            info_result['data']

    def _get_payform(self):
        self.user = get_user(self.request)
        self.trades = Trade.objects.filter(pk__in=self.request.data.getlist('trades'))
        if len(self.trades) == 0:
            self.response = Response({'code': -2, 'result': "데이터가 없습니다."})
            return False
        if len(self.trades) == 1:
            self.name = self.trades[0].product.name
        else:
            self.name = self.trades[0].product.name + ' 외 ' + str(len(self.trades) - 1) + '건'
        self.products = Product.objects.filter(trade__in=self.trades)
        self.create_payment()
        self.payform = PayFormSerializer(
            data=self.request.data,
            context={'name': self.name,
                     'products': self.products,
                     'user': self.user,
                     'order_id': self.payment.order_id}
        )
        return True

    @action(methods=['post'], detail=False)
    def get_payform(self, request):
        """
        method: POST
        :param request:
        :return: code, status and result
        """
        self.request = request
        if not self._get_payform():
            return self.response    # set self.payform
        if not self.is_valid_products():
            return self.response
        if self.payform.is_valid():
            return Response({'code': 1, 'result': self.payform.data})
        return Response(self.payform.errors)

    def set_address(self):
        if hasattr(self.request.data, 'address'):
            self.address = self.request.data['address']
        else:
            self.address = get_object_or_404(Profile, user=self.user).address1

    def create_delivery(self, seller):
        self.delivery = Delivery.objects.create(
            sender=seller,
            receiver=self.user,
            address=self.address,
            state='STEP0',
            number=None,
            mountain=self.request.data['mountain']
        )

    def link_deal(self):
        for deal in self.request.data.getlist('deal'):  # 1 item = 1 deal
            self.create_delivery(deal['seller'])
            self.deal = Deal.objects.create(
                seller=deal['seller'],
                buyer=self.user,
                payment=self.payment,
                total=deal['total'],
                remain=deal['total'],
                delivery=self.delivery
            )
            # link deal to payment, and trades to deal
            self.payment.deal_set.add(deal)
            for trade in self.deal['trades']:
                trade = Trade.objects.get(pk=trade)
                self.deal.trade_set.add(trade)

    @action(methods=['post'], detail=False)
    def confirm(self, request):
        """
        method: POST
        :param request:
        :return: code and status
        """
        self.products = Product.objects.filter(pk__in=request.data.getlist('products'))
        if not self.is_valid_products():
            self.create_payment()
            return self.response
        return Response({"code": -1}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def done(self, request):
        """
        method: POST
        :param request:
        :return: status, code
        """
        # request = {receipt_id, address, deal:[{seller, trades, total, delivery_charge}]}
        self.request = request
        self.user = get_user(self.request)
        self.set_address()
        self.update_payment()
        self.link_deal()

        trades = Trade.objects.filter(pk__in=request.data.getlist('trades'))
        products = Product.objects.filter(trades__in=trades)
        if self.is_valid_products():
            products.update(sold=True)
            trades.update(status=2)
            return Response({"code": 3}, status=status.HTTP_200_OK)
        return Response({"code": -1}, status=status.HTTP_200_OK)

    def canceled(self, request):
        pass

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
