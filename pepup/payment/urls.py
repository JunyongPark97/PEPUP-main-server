from django.urls import path,include
from . import views
from .routers import router

app_name = 'payment'

urlpatterns = [
    path('pay_test/', views.pay_test),
    path('', include(router.urls)),
]

