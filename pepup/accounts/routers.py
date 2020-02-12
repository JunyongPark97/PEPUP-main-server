from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, KakaoUserViewSet, GoogleUserViewSet

router = DefaultRouter()
router.register('', AccountViewSet, basename='accounts')
router.register('kakao', KakaoUserViewSet, basename='kakao')