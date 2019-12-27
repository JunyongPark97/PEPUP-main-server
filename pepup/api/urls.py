from django.urls import path
from . import views
app_name = 'api'


urlpatterns = [
    path('getusers/', views.ListUsers.as_view()),
    path('products/', views.ProductList.as_view()),
    path('products/<int:pk>', views.ProductDetail.as_view()),
]