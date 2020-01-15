from django.test import TestCase
from rest_framework.test import APIRequestFactory

# Create your tests here.
factory = APIRequestFactory()
request = factory.post('/brand/',{'brand_name':'나이키'},format='json')
