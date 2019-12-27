from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import authentication_classes
from rest_framework.renderers import JSONRenderer
from rest_framework import status
from django.http import Http404


# model
from accounts.models import User
from .models import Product

#serializer
from .serializers import ProductSerializer


# Create your views here.
class ListUsers(APIView):

    @authentication_classes(authentication.TokenAuthentication)
    def get(self, request, format=None):
        """
        Return a list of all users.
        """
        email = [user.email for user in User.objects.all()]
        return Response(email)


class ProductList(APIView):
    @authentication_classes(authentication.TokenAuthentication)
    def get(self,request, format=None):
        try:
            products = Product.objects.all()
        except Product.DoesNotExist:
            raise Http404
        serializer = ProductSerializer(Product,many=True)
        return JSONRenderer(serializer.data)

    @authentication_classes(authentication.TokenAuthentication)
    def post(self, request, format=None):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JSONRenderer(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetail(APIView):
    def get_object(self, pk):
        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            raise Http404

    @authentication_classes(authentication.TokenAuthentication)
    def get(self, request, pk, format=None):
        product = self.get_object(pk)
        serializer = ProductSerializer(Product)
        return JSONRenderer(serializer.data)

