from datetime import datetime

from django.shortcuts import render
import json
import uuid

import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, mixins
from rest_framework.decorators import authentication_classes, action
from rest_framework import status, viewsets
from rest_framework import exceptions

from django.db.models import F, Sum, Count, ExpressionWrapper
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.db.models import Q as q
from django.db import transaction
from django.db.models import IntegerField, Value, Case, When
from django.db.models.functions import Ceil

from payment.models import Deal


class PurchasedViewSet(viewsets.ModelViewSet):
    serializer_class = None
    permission_classes = [IsAuthenticated, ]
    queryset = Deal.objects.all()

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset().filter(buyer=user).filter(status__in=[2, 3, 4, 5, 6])

