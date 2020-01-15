from django.urls import path
from . import views
from .routers import router_account

app_name = 'accounts'


urlpatterns = [
    # path('phoneconfirm/', views.PhoneConfirmView.as_view()),
    # path('phoneconfirm/<str:confirm_key>', views.PhoneConfirmView.as_view()),
] + router_account.urls