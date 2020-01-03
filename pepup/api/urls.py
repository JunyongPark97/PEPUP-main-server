from django.urls import path
from django.conf import settings
from . import views


app_name = 'api'


urlpatterns = [
    path('products/', views.ProductList.as_view()),
    path('products/<int:pk>', views.ProductDetail.as_view()),
    path('pay_test/', views.pay_test),
    path('payinfo/',views.PayInfo.as_view())
]

