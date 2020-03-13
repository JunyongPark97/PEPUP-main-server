from django.urls import path, include
from . import views
from .routers import router
from .views import search_address_page

app_name = 'accounts'


urlpatterns = [
    path('', include(router.urls)),
    path('search_address/', search_address_page),
]

