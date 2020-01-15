from django.urls import path,include
from django.conf import settings
from . import views
from .routers import router, router_trades, router_follow

app_name = 'api'

urlpatterns = [
    # path('products/', views.ProductList.as_view()),
    # path('products/<int:pk>', views.ProductDetail.as_view()),
    # path('products/search/<str:search>', views.ProductSearch.as_view()),
    # path('products/filter/', views.ProductFilter.as_view()),
    # path('products/<int:pk>/bagging/', views.Bagging.as_view()),

    path('pay_test/', views.pay_test),
    path('payinfo/', views.PayInfo.as_view()),
    path('brand/', views.BrandView.as_view()),
] + router.urls + router_trades.urls + router_follow.urls

