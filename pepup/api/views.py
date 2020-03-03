import json
import uuid

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
from accounts.models import User, DeliveryPolicy
from payment.models import Trade
from .models import (Product, ProdThumbnail,
                     Brand, Like, Follow,
                     Tag, FirstCategory, SecondCategory, Size, GenderDivision, ProdImage)

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
)

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
            prefetch_related('prodthumbnail_set').all()

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
        ).prefetch_related('prodthumbnail_set').all()

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
        Product 생성하는 api 입니다.
        [Image, tag, name, price, content, size,
        first_category, second_category, brand] 를 받아 생성하며
        Image, tag 는 따로 생성합니다.
        """
        user = request.user
        if not hasattr(user, 'delivery_policy'):
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        data = request.data.copy()

        if not 'image' in data:
            return Response({"message": "Creating needs Image"}, status=status.HTTP_400_BAD_REQUEST)

        image_data = data.pop('image')

        if '' in image_data:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not 'tag' in data:
            return Response({"message": "Creating needs Tag"}, status=status.HTTP_400_BAD_REQUEST)

        tags = data.pop('tag')

        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            data = serializer.validated_data
            data.update({'images': image_data})
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
        Product 업데이트 api 입니다.
        먼저 user가 권한이 있는지(작성자) 확인합니다.
        image는 한장 이상이어야 합니다.
        """
        data = request.data.copy()

        if not 'image' in data:
            return Response({"message": "Updating needs one more Image"}, status=status.HTTP_400_BAD_REQUEST)

        if '' in data['image']:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        instance = self.get_object()
        user = request.user

        if instance.seller.id != user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        image_data = data.pop('image')

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        # remove prod images
        product.images.all().delete()

        # remove prod thumbnail image
        product.prodthumbnail_set.all().delete()

        # Images re-create
        for image in image_data:
            ProdImage.objects.create(product=product, image= image)

        # Thumbnail re-create
        thumbnail = image_data[0]
        ProdThumbnail.objects.update_or_create(product=product, thumbnail=thumbnail)

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
        Product 를 삭제하지 않고 is_active=False 로 변환합니다.
        """
        instance = self.get_object()
        user = request.user
        if instance.seller.id != user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['put'], detail=True)
    def sold(self, request, *args, **kwargs):
        """
        Product 작성자가 sold 처리 or 복구시 호출하는 api 입니다.
        sold 를 반전하여 return 합니다.
        """
        instance = self.get_object()
        user = request.user
        if instance.seller.id != user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        sold = instance.sold
        if sold:
            instance.sold = False
        else:
            instance.sold = True
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
        is_bagged = Trade.objects.filter(product=product, buyer=user)
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
        filtered_products = self.get_queryset()\
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
        Other (선택안함) 이 최상단에 있도록 설정
        """
        result = self.get_ordered_queryset()
        serializer = self.get_serializer(result, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False)
    def searching(self, request, *args, **kwargs):
        """
        brand 검색을 할 때 각 글자에 해당하는 brand 를 조회하는 api 입니다.
        Other (선택안함) 은 검색되지 않음.
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
        tag page 에서 tag 검색을 할 때 각 글자에 해당하는 태그를 조회하는 api 입니다.
        없는 태그의 경우 create 를 TagViewSet에서 하지 않고 ProductViewSet의 create 에서 생성됩니다.
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
        self.recommended_seller = User.objects.all()
        if self.recommended_seller.count() > 10:
            self.recommended_seller = self.recommended_seller[:10]
        # todo: recommend query
        ########
        # todo: serializer 최적화
        self.recommended = UserSerializer(self.recommended_seller, many=True)

    def get_products_by_follow(self):
        follows = Follow.objects.filter(_from=self.user)
        self.follows_by_seller = follows.filter(tag=None, is_follow=True)
        self.follows_by_tag = follows\
            .prefetch_related('tag')\
            .filter(_to=None, is_follow=True)

        self.products_by_seller = Product.objects\
            .select_related('seller', 'brand')\
            .select_related('seller__profile')\
            .prefetch_related('seller___to')\
            .prefetch_related('tag')\
            .filter(seller___to__in=self.follows_by_seller)

        self.products_by_tag = Product.objects\
            .select_related('brand', 'seller', 'second_category', 'second_category__parent') \
            .select_related('seller__profile') \
            .prefetch_related('seller___to') \
            .prefetch_related('tag')\
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
        # qs_ids = list(qs.values_list('id', flat=True))

        # likes_ids = list(Like.objects.filter(product_id__in=qs_ids,
        #                                      user=self.user,
        #                                      is_liked=True).values_list('product_id', flat=True))

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer_class()
        serializer = serializer(page, many=True,
                                context={"request": self.request, "by_seller": p_ids})
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
        print(tag)
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
            return Response({'status': '요청바디가 없습니다.'},status=status.HTTP_400_BAD_REQUEST)
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
        검색 시 한 글자마다 자동완성 해 주는 api
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
        [POST] product name 이 포함된 products 상품을 return 합니다.
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

        if not retrieve_user:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        store_serializer = StoreSerializer(retrieve_user)

        products = retrieve_user.product_set.all().order_by('-created_at')

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

        likes = retrieve_user.liker.filter(is_liked=True)

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


class ReviewViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated, ]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Deal 별로 생성되는 review create
        생성된 리뷰는 수정 및 삭제가 불가능 함.
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
        Sell 버튼을 눌렀을 때 처음으로 호출되는 api
        StoreAccount 모델과 동시에 생성됩니다.
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
        update : 배송비수정 & 배송정책수정
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_206_PARTIAL_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        """
        retrieve
        """
        return super(DeliveryPolicyViewSet, self).retrieve(request, *args, **kwargs)


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


class UploadS3ImageTestAPIView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated,]
    serializer_class = None