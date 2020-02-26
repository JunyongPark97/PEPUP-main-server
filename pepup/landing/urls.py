from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views
from .views import LandingViewSet

router = SimpleRouter()
router.register('', LandingViewSet)

app_name = 'landing'

urlpatterns = [
    path('', views.home),
    path('', include(router.urls))
]