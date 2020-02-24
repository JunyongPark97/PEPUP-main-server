from django.urls import path,include
from . import views
from chat.routers import router
app_name = 'chat'

urlpatterns = [
    path('', include(router.urls)),
]
