from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

app_name = 'landing'

urlpatterns = [
    path('', views.home, name='home'),
    path('apply/', views.apply, name='apply'),
    path('sell_intro/', views.sell_intro, name='sell_intro'),
    path('success/', views.success, name='success'),
    path('terms-of-use/', views.terms_of_use, name='terms-of-use'),

    path('register/', views.RegisterView.as_view(), name='register'),
]