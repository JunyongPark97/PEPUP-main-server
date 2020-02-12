from django.urls import path,include
from django.conf import settings
from . import views
from .routers import router

app_name = 'api'

urlpatterns = [
    path('pay_test/', views.pay_test),
    path('', include(router.urls)),
]

