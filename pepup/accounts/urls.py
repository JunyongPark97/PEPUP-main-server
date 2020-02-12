from django.urls import path, include
from . import views
from .routers import router

app_name = 'accounts'


urlpatterns = [
    path('', include(router.urls)),
]

