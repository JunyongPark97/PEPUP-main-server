from django.urls import path,include
from django.conf import settings
from . import views
from .routers import router, router_trades, router_follow, router_payment, router_search

app_name = 'api'

urlpatterns = [
    path('pay_test/', views.pay_test),
] + router.urls + router_trades.urls + router_payment.urls + router_follow.urls + router_search.urls

