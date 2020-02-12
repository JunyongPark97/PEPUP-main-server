from rest_framework.routers import Route, DefaultRouter, SimpleRouter, DynamicRoute
from .views import AccountViewSet, KakaoUserViewSet


router = DefaultRouter()
router.register('', AccountViewSet, basename='accounts')
router.register('kakao', KakaoUserViewSet, basename='kakao')
