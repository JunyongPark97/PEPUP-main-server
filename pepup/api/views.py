from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import authentication_classes, action
from rest_framework import status, viewsets, generics
from rest_framework.authtoken.models import Token
from rest_framework import mixins
from rest_framework import pagination

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.db.models import Q as q

# model
from accounts.models import User
from .models import Product, ProdThumbnail, Payment, Brand, Trade,Like,Follow,Tag

# serializer
from .serializers import (
    ProductSerializer,
    PaymentSerializer,
    TradeSerializer,
    BrandSerializer,
    FilterSerializer,
    MainSerializer,
    LikeSerializer,
    FollowSerializer
)
from accounts.serializers import UserSerializer

# bootpay
from .Bootpay import BootpayApi

# utils
from accounts.utils import get_user, get_follower
from api.utils import set_filter, add_key_value
from ast import literal_eval


def pay_test(request):
    return render(request,'pay_test.html')


class ProductViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = pagination.PageNumberPagination

    def list(self, request):
        self.serializer_class = MainSerializer
        try:
            products = Product.objects.all()
        except Product.DoesNotExist:
            raise Http404
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page,many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MainSerializer(products,many=True)
        return Response(serializer.data)

    def check_thum(self, request):
        return Response({})

    def set_prodThumbnail(self, product, request):
        for thum in request.FILES.getlist('thums'):
            ProdThumbnail.objects.create(
                product=product,
                thumbnail=thum
            )

    def create(self, request):
        seller = get_user(request)
        brand = get_object_or_404(Brand, id=int(request.POST['brand_id']))
        serializer = ProductSerializer(data=request.data,partial=True)
        if serializer.is_valid():
            product=serializer.save(
                seller=seller,
                brand=brand
            )
            self.set_prodThumbnail(product,request)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def search(self, request, pk):
        query = q(name__icontains=pk) | q(seller__nickname__icontains=pk) | q(brand__name__icontains=pk)
        products = Product.objects.filter(query)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MainSerializer(products,many=True)
        serializers = ProductSerializer(products, many=True)
        return Response(serializers.data)

    def filter(self, request):
        pass

    def retrieve(self, request, pk, format=None):
        user = get_user(request)
        product = get_object_or_404(Product, pk=pk)
        sold_products = Product.objects.filter(seller=product.seller,sold=True)
        like, tf = Like.objects.get_or_create(user=user, product=product,is_liked=False)
        follower = get_follower(product.seller)
        serializer = ProductSerializer(product)
        return Response({
            'product': serializer.data,
            'liked': like.is_liked,
            'seller': {
                'id': product.seller.id,
                'reviews': 0,
                'sold': len(sold_products),
                'follower': len(follower),
            },
        })

    def like(self, request, pk):
        user = get_user(request)
        product = Product.objects.get(pk=pk)
        like, tf = Like.objects.get_or_create(user=user, product=product)
        print(tf)
        if not tf:
            if like.is_liked:
                like.is_liked = False
            else:
                like.is_liked = True
            like.save()
        serializer = LikeSerializer(like)
        return Response(serializer.data)

    def liked(self,request, pk):
        user = get_user(request)
        product = Product.objects.get(pk=pk)
        like = get_object_or_404(Like, user=user,product=product)
        serializer = LikeSerializer(like)
        return Response(serializer.data)

    def update(self, request, pk=None):
        pass

    def partial_update(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass


class TradeViewSet(viewsets.GenericViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer

    def bagging(self, request, pk):
        buyer = get_user(request)
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

    def cart(self, request):
        buyer = get_user(request)
        trades = Trade.objects.filter(buyer=buyer)
        serializer = TradeSerializer(trades, many=True)
        return Response(self.groupbyseller(serializer.data))

    def cancel(self, request):
        ls_cancel = request.data['trades']
        trades = Trade.objects.filter(pk__in=ls_cancel)
        if trades:
            trades.delete()
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)


class ProductDetail(APIView):
    def get_object(self, pk):
        print(get_object_or_404(Product, pk=pk))
        return get_object_or_404(Product, pk=pk)

    # @authentication_classes(authentication.TokenAuthentication)
    def get(self, request, pk, format=None):
        product = self.get_object(pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


class PaymentViewSet(viewsets.GenericViewSet):
    def get_access_token(self):
        bootpay = BootpayApi(application_id='5e05af1302f57e00219c40dd', private_key='wL0YFi+aIVN/wkkV90zSb228IgafRbRcPAV94/Rmu1o=')
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    def get_payform(self, items):
        pass



class PayInfo(APIView):
    # todo : 최적화 필요 토큰을 저장하고 25분마다 생성하고 그 안에서는 있는 토큰 사용할 수 있게
    # todo : private_key 초기화 및 가져오는 처리도 필요
    def get_access_token(self):
        bootpay = BootpayApi(application_id='5e05af1302f57e00219c40dd', private_key='wL0YFi+aIVN/wkkV90zSb228IgafRbRcPAV94/Rmu1o=')
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
        bootpay = BootpayApi(application_id='5e05af1302f57e00219c40dd', private_key='wL0YFi+aIVN/wkkV90zSb228IgafRbRcPAV94/Rmu1o=')
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


class BrandView(APIView):
    def get(self, request):
        brand = Brand.objects.all()
        serializers = BrandSerializer(brand, many=True)
        return JsonResponse(serializers.data, safe=False)

    def post(self, request):
        brand_name = request.data['brand']
        if Brand.objects.filter(name=brand_name).exists():
            return Response({"return": "Already exists"})
        else:
            brand = Brand.objects.create(
                name=brand_name
            )
            serializers = BrandSerializer(brand)
            return JsonResponse(serializers.data)


class FollowViewSet(viewsets.GenericViewSet):
    serializer_class = FollowSerializer
    pagination_class = pagination.PageNumberPagination

    def list(self, request):
        user = get_user(request)
        _toes = Follow.objects.filter(_from=user, tag=None)
        tags = Follow.objects.filter(_from=user, _to=None)
        products_toes = Product.objects.filter(seller_id__in=_toes.values_list('_to',flat=True))
        products_by_tags = Product.objects.filter(tag__in=tags.values_list('tag',flat=True))
        self.serializer_class = ProductSerializer

        page = self.paginate_queryset(products_toes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(products_by_tags,many=True)
        return Response(serializer.data)

    def _check_follow(self,_from, _to, tag):
        follows = Follow.objects.get(q(_from=_from)&(q(_to=_to)|q(tag=tag)))
        if follows:
            return follows
        else:
            return False

    def check_follow(self, request):
        _from = get_user(request)
        follow = self._check_follow(_from,request.POST['_to'],request.POST['tag'])
        if follow:
            return Response(FollowSerializer(follow))
        return Response({'status':'no following'})

    def _following(self, _from, _to, tag):
        if _to:
            _to = get_object_or_404(User,pk=_to)
            follow, created = Follow.objects.get_or_create(_from=_from, _to=_to)
        else:
            tag = get_object_or_404(Tag, pk=tag)
            follow, created = Follow.objects.get_or_create(_from=_from, tag=tag)
        if not created:
            if follow.is_follow:
                follow.is_follow = False
            else:
                follow.is_follow = True
            follow.save()
            return FollowSerializer(follow).data
        return FollowSerializer(follow).data

    def following(self, request):
        _from = get_user(request)
        return Response(self._following(_from,_to=request.POST['_to'],tag=request.POST['tag']))