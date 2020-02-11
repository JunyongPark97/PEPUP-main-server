from django.urls import path, include
from . import views
from .routers import router

app_name = 'accounts'


urlpatterns = [
    path('', include(router.urls)),
    # path('', include(router_account.urls)),
    # path('kakao/', include(router_social.urls))
]
