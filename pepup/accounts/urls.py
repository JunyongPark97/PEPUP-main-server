from django.urls import path
from . import views
from rest_framework import routers
app_name = 'accounts'


urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('signup/',views.SignupView.as_view()),
    path('phoneconfirm/', views.PhoneConfirmView.as_view()),
    path('phoneconfirm/<str:confirm_key>', views.PhoneConfirmView.as_view()),
]