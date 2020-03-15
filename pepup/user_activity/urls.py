from django.urls import path,include
from .routers import router

app_name = 'purchased'

urlpatterns = [
    path('', include(router.urls)),
]

