from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import authentication_classes
from rest_framework import status
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render

# model
from accounts.models import User
from .models import Product,Payment,Brand

# serializer
from .serializers import ProductSerializer, PaymentSerializer

# bootpay
from .Bootpay import BootpayApi

def pay_test(request):
    return render(request,'pay_test.html')


class ProductList(APIView):
    @authentication_classes(authentication.TokenAuthentication)
    def get(self, request, format=None):
        try:
            products = Product.objects.all()
        except Product.DoesNotExist:
            raise Http404
        serializer = ProductSerializer(products, many=True)
        return JsonResponse(serializer.data, safe=False)

    @authentication_classes(authentication.BasicAuthentication)
    def post(self, request, format=None):
        brand = Brand.objects.get(id=int(request.POST['brand_id']))
        seller = User.objects.get(email=request.POST['seller_id'])
        request.data['brand'] = brand.pk
        request.data['seller'] = seller.pk
        serializer = ProductSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetail(APIView):
    def get_object(self, pk):
        print(get_object_or_404(Product, pk=pk))
        return get_object_or_404(Product, pk=pk)

    # @authentication_classes(authentication.TokenAuthentication)
    def get(self, request, pk, format=None):
        product = self.get_object(pk)
        serializer = ProductSerializer(product)
        return JsonResponse(serializer.data)


class PayInfo(APIView):
    # todo : 최적화 필요 토큰을 저장하고 25분마다 생성하고 그 안에서는 있는 토큰 사용할 수 있게
    # todo : private_key 초기화 및 가져오는 처리도 필요
    def get_access_token(self):
        bootpay = BootpayApi(application_id='5e05af1302f57e00219c40dd', private_key='wL0YFi+aIVN/wkkV90zSb228IgafRbRcPAV94/Rmu1o=')
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    @authentication_classes(authentication.TokenAuthentication)
    def get(self, request, format=None):
        bootpay = self.get_access_token()
        receipt_id = request.META.get('HTTP_RECEIPTID')
        info_result = bootpay.verify(receipt_id)
        if info_result['status'] is 200:
            return JsonResponse(info_result)

    @authentication_classes(authentication.TokenAuthentication)
    def post(self, request):
        bootpay = self.get_access_token()
        receipt_id = request.META.get('HTTP_RECEIPTID')
        info_result = bootpay.verify(receipt_id)
        if info_result['status'] is 200:
            all_fields = Payment.__dict__.keys()
            filtered_dict = {}
            for key in info_result['data']:
                if key in all_fields:
                    filtered_dict[key] = info_result['data'][key]
            payment = Payment.objects.create(**filtered_dict)
            print(payment)
            serializer = PaymentSerializer(payment)
            serializer.save()
            return JsonResponse(serializer.data)
        else:
            return JsonResponse(info_result)


class RefundInfo(APIView):
    # todo: 부트페이 계정 초기화 및 일반화
    def get_access_token(self):
        bootpay = BootpayApi(application_id='5e05af1302f57e00219c40dd', private_key='wL0YFi+aIVN/wkkV90zSb228IgafRbRcPAV94/Rmu1o=')
        result = bootpay.get_access_token()
        if result['status'] is 200:
            return bootpay

    def post(self,request, format=None, **kwargs):
        bootpay = self.get_access_token()
        receipt_id = request.META.get('HTTP_RECEIPTID')
        refund = request.data
        print(refund)
        cancel_result = bootpay.cancel(receipt_id, refund['name']['amount'], refund['name']['name'], refund['name']['description'])
        if cancel_result['status'] is 200:
            return JsonResponse(cancel_result)
        else:
            return JsonResponse(cancel_result)
