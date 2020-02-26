from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views
from .views import LandingViewSet

router = SimpleRouter()
router.register('', LandingViewSet)

app_name = 'landing'

urlpatterns = [
    path('', views.home, name='home'),
    path('apply/', views.apply, name='apply'),
    path('sell_intro/', views.sell_intro, name='sell_intro'),
    path('success/', views.success, name='success'),

    path('register/', views.RegisterView.as_view(), name='register'),
    # path('', include(router.urls))
]