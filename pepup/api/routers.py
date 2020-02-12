from rest_framework.routers import Route, DefaultRouter,SimpleRouter, DynamicRoute
from .views import (
    ProductViewSet, TradeViewSet, FollowViewSet,
    PaymentViewSet,
    SearchViewSet)


router = DefaultRouter()
router.register('products', ProductViewSet, basename='products')
router.register('trades', TradeViewSet, basename='trades')
router.register('follow', FollowViewSet, basename='follow')
router.register('payment', PaymentViewSet, basename='payment')
router.register('search',SearchViewSet, basename='search')