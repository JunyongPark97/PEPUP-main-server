
from rest_framework.routers import Route, DefaultRouter, DynamicRoute
from .views import (
    ProductViewSet, FollowViewSet,
    SearchViewSet, StoreViewSet, ReviewViewSet, DeliveryPolicyViewSet, ProductCategoryAPIViewSet, TagViewSet,
    BrandViewSet, S3ImageUploadViewSet, ProfileViewSet)


class CustomRouter(DefaultRouter):
    routes = [
        # List route.
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
                'post': 'create'
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        # Dynamically generated list routes. Generated using
        # @action(detail=False) decorator on methods of the viewset.
        DynamicRoute(
            url=r'^{prefix}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={}
        ),
        # Detail route.
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated detail routes. Generated using
        # @action(detail=True) decorator on methods of the viewset.
        DynamicRoute(
            url=r'^{prefix}/{url_path}/{lookup}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        ),
    ]


router = CustomRouter()
router.register('products', ProductViewSet, basename='products')
router.register('follow', FollowViewSet, basename='follow')
router.register('search', SearchViewSet, basename='search')
router.register('store', StoreViewSet, basename='shop')
router.register('review', ReviewViewSet, basename='review')
router.register('delivery-policy', DeliveryPolicyViewSet, basename='review')
router.register('category', ProductCategoryAPIViewSet, basename='review')
router.register('tag', TagViewSet, basename='review')
router.register('brand', BrandViewSet, basename='review')
router.register('s3', S3ImageUploadViewSet, basename='s3')
router.register('profile', ProfileViewSet, basename='s3')
