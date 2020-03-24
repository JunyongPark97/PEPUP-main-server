from django.urls import path, include
from .routers import router

app_name = 'notice'

urlpatterns = [
    path('', include(router.urls)),
]

