import base64
import datetime
import hashlib
import hmac
import json
import uuid

import boto3
import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework import status, viewsets
from django.db.models import F, Count, ExpressionWrapper
from django.http import Http404
from django.db.models import Q as q
from django.db import transaction
from django.db.models import IntegerField, Value, Case, When
from django.db.models.functions import Ceil

# model
from accounts.models import User, DeliveryPolicy, Profile, StoreAccount
from payment.models import Trade
from .loader import load_credential
from .models import (Product, ProdThumbnail,
                     Brand, Like, Follow,
                     Tag, FirstCategory, SecondCategory, Size, GenderDivision, ProdImage, ProdS3Image)

# serializer
from .serializers import (
    ProductSerializer,
    BrandSerializer,
    MainSerializer,
    LikeSerializer,
    FollowSerializer,
    SearchResultSerializer, DeliveryPolicySerializer, RelatedProductSerializer, FollowingSerializer,
    StoreSerializer, StoreLikeSerializer, FirstCategorySerializer, SecondCategorySerializer,
    GenderSerializer, SizeSerializer, ProductCreateSerializer, ReviewCreateSerializer,
    SimpleProfileSerializer, StoreReviewSerializer, DeliveryPolicyWriteSerializer,
    StoreProfileRetrieveSerializer, StoreAccountSerializer, StoreAccountWriteSerializer)

from accounts.serializers import UserSerializer

from api.pagination import FollowPagination, HomePagination, ProductSearchResultPagination, \
    TagSearchResultPagination, StorePagination, StoreReviewPagination

# bootpay
from payment.Bootpay import BootpayApi

# utils
from .utils import generate_s3_presigned_post


class ProductViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.filter(is_active=True)
    pagination_class = HomePagination
    permission_classes = [IsAuthenticated, ]
    serializer_class = ProductSerializer

    def get_serializer_class(self):
        if self.action in ['list', 'filter']:
            return MainSerializer
        elif self.action in ['create', 'update']:
            return ProductCreateSerializer
        elif self.action in ['like', 'liked']:
            return LikeSerializer
        return super(ProductViewSet, self).get_serializer_class()

    def list(self, request):
        """
        :method: GET
        :param request:
        :return:
        """
        products = self.get_queryset().\
            select_related('prodthumbnail').all()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset=products, request=request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['post'], detail=False)
    def filter(self, request, *args, **kwargs):
        filter_data = self.request.data.copy()

        queryset = self.get_queryset()\
            .select_related(
            'brand',
            'first_category',
            'first_category__gender',
            'second_category',
            'size',
            'seller__delivery_policy',
            'second_category__parent',
            'prodthumbnail'
            ).all()

        if 'gender' in filter_data:
            gender = filter_data.pop('gender')  # gender obj id(int)
            queryset = queryset \
                .filter(first_category__isnull=False) \
                .filter(first_category__gender_id=gender)

        if 'first_category' in filter_data:
            first_category = filter_data.pop('first_category')
            queryset = queryset \
                .filter(first_category_id=first_category)

        if 'second_category' in filter_data:
            second_category = filter_data.pop('second_category')
            queryset = queryset \
                .filter(second_category_id=second_category)

        if 'size' in filter_data:
            size = filter_data.pop('size')
            queryset = queryset \
                .filter(size_id=size)

        if 'brand' in filter_data:
            brand = filter_data.pop('brand')
            queryset = queryset \
                .filter(brand_id=brand)

        if 'on_sale' in filter_data:
            on_sale = filter_data.pop('on_sale')
            # on_sale=True
            if on_sale:
                queryset = queryset.filter(on_discount=True)

                # calculate discount price
                queryset = queryset \
                    .annotate(discount_price=ExpressionWrapper(
                    Ceil((F('price') * (1 - F('discount_rate'))) / 100) * 100,
                    output_field=IntegerField()))

                if 'lower_price' in filter_data:
                    lower_price = filter_data.pop('lower_price')
                    queryset = queryset.filter(discount_price__gte=lower_price)

                if 'higher_price' in filter_data:
                    higher_price = filter_data.pop('higher_price')
                    queryset = queryset.filter(discount_price__lte=higher_price)

        # no on_sale data or on_sale=False
        if 'lower_price' in filter_data:
            lower_price = filter_data.pop('lower_price')
            queryset = queryset.filter(price__gte=lower_price)

        if 'higher_price' in filter_data:
            higher_price = filter_data.pop('higher_price')
            queryset = queryset.filter(price__lte=higher_price)

        if 'free_delivery' in filter_data:
            queryset = queryset.filter(seller__delivery_policy__general=0)

        products = queryset

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
        Product ???????????? api ?????????.
        [Image, tag, name, price, content, size,
        first_category, second_category, brand] ??? ?????? ????????????
        Image, tag ??? ?????? ???????????????.
        """
        user = request.user
        if not hasattr(user, 'delivery_policy'):
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        data = request.data.copy()
        if not 'image_key' in data:
            return Response({"message": "Creating needs Image"}, status=status.HTTP_400_BAD_REQUEST)

        image_data = data.pop('image_key')

        if '' in image_data:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not 'tag' in data:
            return Response({"message": "Creating needs Tag"}, status=status.HTTP_400_BAD_REQUEST)

        tags = data.pop('tag')

        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            data = serializer.validated_data
            data.update({'image_keys': image_data})
            product = serializer.create(data)

            # tag relation
            for tag_value in tags:
                tag, _ = Tag.objects.get_or_create(tag=tag_value)
                product.tag.add(tag.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        """
        Product ???????????? api ?????????.
        ?????? user??? ????????? ?????????(?????????) ???????????????.
        image_key??? ?????? ??????????????? ?????????.
        """
        data = request.data.copy()

        if not 'image_key' in data:
            return Response({"message": "Updating needs one more Image"}, status=status.HTTP_400_BAD_REQUEST)

        if '' in data['image_key']:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        instance = self.get_object()
        user = request.user

        if instance.seller.id != user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        image_keys = data.pop('image_key')

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        # remove prod images
        product.images.all().delete()

        # remove prod thumbnail image
        product.prodthumbnail.delete()

        # Images re-create
        for image_key in image_keys:
            ProdS3Image.objects.create(product=product, image_key=image_key)

        # Thumbnail re-create
        ProdThumbnail.objects.create(product=product)

        # if tag changed , tag update
        if 'tag' in data:
            tags = data.pop('tag')

            # tag remove
            exist_tags = product.tag.all()
            for exist_tag in exist_tags:
                product.tag.remove(exist_tag)

            # tag update
            for tag_value in tags:
                tag, _ = Tag.objects.get_or_create(tag=tag_value)
                product.tag.add(tag)

        return Response(serializer.data, status=status.HTTP_206_PARTIAL_CONTENT)

    def destroy(self, request, *args, **kwargs):
        """
        Product ??? ???????????? ?????? is_active=False ??? ???????????????.
        """
        instance = self.get_object()
        user = request.user
        if instance.seller.id != user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if instance.sold and instance.sold_status == 1:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['put'], detail=True)
    def sold(self, request, *args, **kwargs):
        """
        Product ???????????? sold ?????? or ????????? ???????????? api ?????????.
        sold ??? ???????????? return ?????????.
        """
        instance = self.get_object()
        user = request.user
        if instance.seller.id != user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        sold = instance.sold
        if sold and instance.sold_status == 2:
            instance.sold = False
        else:
            instance.sold = True
            instance.sold_status = 2
        instance.save()
        return Response({'sold': instance.sold}, status=status.HTTP_206_PARTIAL_CONTENT)

    # TODO : TO BE CHANGE SERVER NAME
    def request_classification(self, images):
        server_url = ""
        request_options = [{'version': 1, 'use_cache': True}]
        data = {'image_url': images, 'requests': request_options}
        try:
            result = json.loads(requests.post(server_url, json=data).text)
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
        product = self.get_object()
        try:
            like = Like.objects.get(user=user, product=product)
            is_liked = like.is_liked
        except Like.DoesNotExist:
            is_liked = False
        is_bagged = Trade.objects.filter(product=product, buyer=user, status=1)
        if is_bagged.exists():
            bagged = True
        else:
            bagged = False

        serializer = ProductSerializer(product)

        if not hasattr(product.seller, 'delivery_policy'):
            return Response({"message: User has no Delivery_policy"}, status=status.HTTP_404_NOT_FOUND)

        delivery_policy = DeliveryPolicySerializer(product.seller.delivery_policy)

        related_products = self.get_related_products(product)
        if related_products:
            related_products = RelatedProductSerializer(related_products, many=True).data
        else:
            related_products = []
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
        filtered_products = self.get_queryset()\
            .select_related('size','size__category','size__category__gender')\
            .prefetch_related('tag').\
            exclude(id=product.id).\
            filter(second_category=second_category).\
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
    @action(methods=['post'], detail=True)
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

    @action(methods=['get'], detail=True)
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
            return Response({'status': 'product does not exist'}, status=status.HTTP_404_NOT_FOUND)
        try:
            like = Like.objects.get(user=user, product=product)
        except Like.DoesNotExist:
            return Response({'results': {'is_liked': False}}, status=status.HTTP_200_OK)
        return Response({'results': self.get_serializer(like).data}, status.HTTP_200_OK)


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
        return queryset

    def get_serializer_class(self):
        serializer = FirstCategorySerializer
        if self.action == 'gender':
            serializer = GenderSerializer
        elif self.action == 'second_category':
            serializer = SecondCategorySerializer
        elif self.action == 'size':
            serializer = SizeSerializer
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


class BrandViewSet(viewsets.GenericViewSet):
    queryset = Brand.objects.all()
    permission_classes = [IsAuthenticated, ]
    serializer_class = BrandSerializer

    def list(self, request, *args, **kwargs):
        """
        brand list api
        Other (????????????) ??? ???????????? ????????? ??????
        """
        result = self.get_ordered_queryset()
        serializer = self.get_serializer(result, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False)
    def searching(self, request, *args, **kwargs):
        """
        brand ????????? ??? ??? ??? ????????? ???????????? brand ??? ???????????? api ?????????.
        Other (????????????) ??? ???????????? ??????.
        """
        keyword = request.data['keyword']
        if keyword:
            value = self.get_queryset()\
                    .exclude(name='Other')\
                    .filter(name__icontains=keyword) \
                    .order_by('id')[:15]
            serializer = self.get_serializer(value, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(self.get_ordered_queryset(), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def get_ordered_queryset(self):
        queryset = self.get_queryset()
        other = queryset.filter(name="Other")
        qs = queryset.exclude(name="Other")
        other = list(other)
        qs = list(qs)
        result = other + qs
        return result


class TagViewSet(viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    permission_classes = [IsAuthenticated,]

    @action(methods=['post'], detail=False)
    def searching(self, request, *args, **kwargs):
        """
        tag page ?????? tag ????????? ??? ??? ??? ????????? ???????????? ????????? ???????????? api ?????????.
        ?????? ????????? ?????? create ??? TagViewSet?????? ?????? ?????? ProductViewSet??? create ?????? ???????????????.
        """
        keyword = request.data['keyword']
        if len(keyword) < 2:
            return Response([], status=status.HTTP_200_OK)
        value = self.get_queryset()\
                              .prefetch_related('product_set') \
                              .filter(tag__icontains=keyword) \
                              .annotate(product_count=Count('product')) \
                              .values('tag', 'id') \
                              .order_by('-product_count')[:15]
        return Response(value, status=status.HTTP_200_OK)


class FollowViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = FollowSerializer
    pagination_class = FollowPagination
    permission_classes = [IsAuthenticated]

    def get_recommended_seller(self):
        self.recommended_seller = User.objects.filter(is_active=True)
        if self.recommended_seller.count() > 10:
            self.recommended_seller = self.recommended_seller[:10]
        # todo: recommend query
        ########
        # todo: serializer ?????????
        self.recommended = UserSerializer(self.recommended_seller, many=True)

    def get_products_by_follow(self):
        follows = Follow.objects.filter(_from=self.user).filter(_to__is_active=True)
        self.follows_by_seller = follows.filter(tag=None, is_follow=True)
        self.follows_by_tag = follows\
            .prefetch_related('tag')\
            .filter(_to=None, is_follow=True)

        self.products_by_seller = Product.objects\
            .select_related('seller', 'brand')\
            .select_related('seller__profile')\
            .prefetch_related('seller___to')\
            .prefetch_related('tag')\
            .filter(is_active=True)\
            .filter(seller___to__in=self.follows_by_seller)

        self.products_by_tag = Product.objects\
            .select_related('brand', 'seller', 'second_category', 'second_category__parent') \
            .select_related('seller__profile') \
            .prefetch_related('seller___to') \
            .prefetch_related('tag')\
            .filter(is_active=True)\
            .filter(tag__follow__in=self.follows_by_tag)

    def list(self, request):
        """
        :method: GET
        :param request: header token
        :return: code, status and paginated response
        """

        self.user = request.user
        self.get_products_by_follow()
        self.get_recommended_seller()

        products_by_seller = self.products_by_seller
        products_by_tag = self.products_by_tag

        qs = (products_by_seller | products_by_tag).distinct()

        p_ids = list(products_by_seller.values_list('id', flat=True))

        tag_ids = list(self.follows_by_tag.values_list('tag_id'))
        tag_id_list = []
        for tag_id in tag_ids:
            tag_id_list.append(tag_id[0])

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer_class()
        serializer = serializer(page, many=True,
                                context={"request": self.request, "by_seller": p_ids, "follow_tag_ids": tag_id_list})
        return self.get_paginated_response({"products": serializer.data, "recommended": []})

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
            return Response({'status': '??????????????? ????????????.'},status=status.HTTP_400_BAD_REQUEST)
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
                follow, created = Follow.objects.get_or_create(_from=_from, tag_id=tag.id)
            except Tag.DoesNotExist:
                return Response({'status': "Tag does not exist"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'status': '??????????????? ????????????.'},status=status.HTTP_400_BAD_REQUEST)
        if not created:
            if follow.is_follow:
                follow.is_follow = False
            else:
                follow.is_follow = True
            follow.save()
        return Response({'results': self.get_serializer(follow).data}, status=status.HTTP_200_OK)


class SearchViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = SearchResultSerializer

    @action(methods=['post'],detail=False)
    def searching(self, request):
        """
        ?????? ??? ??? ???????????? ???????????? ??? ?????? api
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
        [POST] product name ??? ????????? products ????????? return ?????????.
        :param request: keyword (string) ?????? ?????? ???
        :return: paginated data, status
        """
        keyword = request.data['keyword']
        if len(keyword) < 1:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            products = Product.objects.filter(name__icontains=keyword, is_active=True).order_by('-created_at')
        except Product.DoesNotExist:
            raise Http404

        paginator = ProductSearchResultPagination()
        page = paginator.paginate_queryset(products, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['get'], detail=True, serializer_class=MainSerializer)
    def tag_search(self, request, pk):
        """
        searching api ?????? ???????????? tag_id ???????????? ????????? return ?????????.
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
        products = Product.objects.filter(tag=tag, is_active=True).order_by('-created_at')
        page = paginator.paginate_queryset(queryset=products, request=request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data, tag_followed=tag_followed)

    def search_by_product(self, keyword):
        searched_product = Product.objects.filter(name__icontains=keyword).filter(is_active=True)
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
            .filter(nickname__icontains=keyword, is_active=True)\
            .order_by('nickname')[:5]
        return queryset


class StoreViewSet(viewsets.GenericViewSet):
    pagination_class = StorePagination
    permission_classes = [IsAuthenticated, ]

    def get_serializer_class(self):
        if self.action == 'shop':
            serializer = MainSerializer
        elif self.action == 'like':
            serializer = StoreLikeSerializer
        elif self.action == 'review':
            serializer = SimpleProfileSerializer
        else:
            serializer = super(StoreViewSet, self).get_serializer_class()
        return serializer

    @action(methods=['get'], detail=True)
    def shop(self, request, *args, **kwargs):
        """
        Store main retrieve api
        """
        retrieve_user = self.get_retrieve_user(kwargs['pk'])
        user = request.user
        if not retrieve_user:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        # get user followed
        try:
            user_followed = Follow.objects.get(_to=retrieve_user, _from=user).is_follow
        except:
            user_followed = False

        store_serializer = StoreSerializer(retrieve_user, context={'user_followed': user_followed})

        products = retrieve_user.product_set.filter(is_active=True).order_by('-created_at')

        paginator = StorePagination()
        page = paginator.paginate_queryset(queryset=products, request=request)
        products_serializer = self.get_serializer(page, many=True)

        return paginator.get_paginated_response(products_serializer.data, profile=store_serializer.data)

    @action(methods=['get'], detail=True)
    def like(self, request, *args, **kwargs):
        """
        Store's like retrieve api
        """
        retrieve_user = self.get_retrieve_user(kwargs['pk'])
        if not retrieve_user:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        likes = retrieve_user.liker.filter(is_liked=True, product__is_active=True)

        paginator = StorePagination()
        page = paginator.paginate_queryset(queryset=likes, request=request)
        products_serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(products_serializer.data)

    @action(methods=['get'], detail=True)
    def review(self, request, *args, **kwargs):
        """
        Store's review retrieve api
        """
        retrieve_user = self.get_retrieve_user(kwargs['pk'])

        if not retrieve_user:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        simple_profile_serializer = self.get_serializer(retrieve_user)

        reviews = retrieve_user.received_reviews
        paginator = StoreReviewPagination()

        if not reviews.first():
            return paginator.get_paginated_response(simple_profile_serializer.data)

        reviews = reviews.all()
        page = paginator.paginate_queryset(queryset=reviews, request=request)
        review_serializer = StoreReviewSerializer(page, many=True)

        return paginator.get_paginated_response(simple_profile_serializer.data, data=review_serializer.data)

    def get_retrieve_user(self, pk):
        try:
            retrieve_user = User.objects.get(pk=pk)
        except:
            retrieve_user = None
        return retrieve_user


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = StoreProfileRetrieveSerializer
    permission_classes = [IsAuthenticated, ]

    def retrieve(self, request, *args, **kwargs):
        """
        store??? profile ?????? ??? ???????????? api ?????????.
        """
        # check acceptable
        user = request.user
        retrieve_user = self.get_object()
        if user != retrieve_user:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        return super(ProfileViewSet, self).retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        store??? profile ???????????? api ?????????.
        introduce, nickname, profile_img ??? params??? ????????????.
        """
        data = request.data.copy()
        profile = self.get_object().profile

        # check acceptable
        user = request.user
        retrieve_user = self.get_object()
        if user != retrieve_user:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        if 'introduce' in data:
            introduce = data.pop('introduce')
            profile.introduce = introduce[0]
            profile.save()

        if 'nickname' in data:
            nickname = data.pop('nickname')
            user.nickname = nickname[0]
            user.save()

        if 'profile_img' in request.FILES:
            prof_img = request.FILES['profile_img']
            profile.thumbnail_img = prof_img
            profile.save()

        return Response(status=status.HTTP_206_PARTIAL_CONTENT)


class ReviewViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated, ]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Deal ?????? ???????????? review create
        ????????? ????????? ?????? ??? ????????? ????????? ???.
        """
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Done!
            serializer.create(data)
            return Response(status=status.HTTP_201_CREATED)

        return Response(status=status.HTTP_400_BAD_REQUEST)


class DeliveryPolicyViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin,
                            mixins.UpdateModelMixin, mixins.RetrieveModelMixin):
    permission_classes = [IsAuthenticated, ]
    serializer_class = DeliveryPolicyWriteSerializer
    queryset = DeliveryPolicy.objects.all()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Sell ????????? ????????? ??? ???????????? ???????????? api
        StoreAccount ????????? ????????? ???????????????.
        :param request: bank(int), account(int), account_holder(String), general(int), mountain(int)
        """
        user = request.user

        if hasattr(user, 'delivery_policy'):
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        data = request.data.copy()
        account_data = {}
        bank = data.pop('bank', None)
        account = data.pop('account', None)
        account_holder = data.pop('account_holder', None)
        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            data = serializer.validated_data
            account_data.update({'bank': bank})
            account_data.update({'account': account})
            account_data.update({'account_holder': account_holder})
            data.update({'account_data': account_data})

            # Done!
            serializer.create(data)

            return Response(status=status.HTTP_201_CREATED)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        update : ??????????????? & ??????????????????
        """
        user = request.user
        if not hasattr(user, 'delivery_policy'):
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        instance = user.delivery_policy
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_206_PARTIAL_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        """
        retrieve
        """
        return None

    @action(methods=['get'], detail=False)
    def owner(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(user, 'delivery_policy'):
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        instance = user.delivery_policy
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class StoreAccountViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    # serializer_class = StoreAccountSerializer
    permission_classes = [IsAuthenticated, ]

    def get_serializer_class(self):
        serializer = StoreAccountSerializer
        if self.action == 'retrieve':
            serializer = serializer
        elif self.action in ['create', 'update']:
            serializer = StoreAccountWriteSerializer
        else:
            serializer = serializer
        return serializer

    def retrieve(self, request, *args, **kwargs):
        retrieve_user = self.get_object()
        user = request.user

        # check acceptable
        if not retrieve_user == user:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        if not hasattr(retrieve_user, 'account'):
            return Response(None, status=status.HTTP_204_NO_CONTENT)

        serializer = self.get_serializer(retrieve_user.account)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        retrieve_user = self.get_object()
        user = request.user

        # check acceptable
        if not retrieve_user == user:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        data = request.data.copy()
        account = retrieve_user.account
        serializer = self.get_serializer(account, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_206_PARTIAL_CONTENT)

    @action(methods=['get'], detail=False)
    def banks(self, request, *args, **kwargs):
        banks = StoreAccount.BANK
        bank_list = []
        for bank in banks:
            a = {}
            a['bank_id'] = bank[0]
            a['bank'] = bank[1]
            bank_list.append(a)
        return Response(bank_list, status=status.HTTP_200_OK)


class S3ImageUploadViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, ]

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated, ])
    def key(self, request):
        """
        s3 policy generate
        """
        ext = request.GET.get('ext', 'jpg')
        if ext not in ('jpg', 'mp3', 'mp4'):
            ext = 'jpg'
        key = uuid.uuid4()
        expiry = 60 * 60 * 24
        data = generate_s3_presigned_post('pepup-storage', key, expiry, ext, )
        return Response(data)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated, ])
    def temp_key(self, request):
        ext = request.GET.get('ext', 'jpg')
        if ext not in ('jpg', 'mp3', 'mp4'):
            ext = 'jpg'
        key = uuid.uuid4()
        image_key = "%s.%s" % (key, ext)
        url = "https://{}.s3.amazonaws.com/".format('pepup-storage')
        content_type = "image/jpeg"
        data = {"url": url, "image_key": image_key, "content_type": content_type, "key":key}
        return Response(data)

    def fun_temp_key(self):
        # ext = request.GET.get('ext', 'jpg')
        # if ext not in ('jpg', 'mp3', 'mp4'):
        ext = 'jpg'
        key = uuid.uuid4()
        image_key = "%s.%s" % (key, ext)
        url = "https://{}.s3.amazonaws.com/".format('pepup-storage')
        content_type = "image/jpeg"
        data = {"url": url, "image_key": image_key, "content_type": content_type, "key":key}
        return data

    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated, ])
    def temp_key_list(self, request):
        data = request.data
        count = int(data['count'])
        print(count)
        temp_key_list = []
        for i in range(count):
            temp_key = self.fun_temp_key()
            temp_key_list.append(temp_key)
        print(temp_key_list)
        return Response(temp_key_list)
