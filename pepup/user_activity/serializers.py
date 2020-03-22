from datetime import timedelta, datetime

from rest_framework import serializers
from payment.models import Deal, Review, Delivery


class PurchasedDealSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    condition = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = ['id', 'status', 'name', 'total', 'thumbnail', 'condition']

    def get_status(self, obj):
        if obj.status == 2:
            return '결제완료'
        elif obj.status in [3, 4]: # 3: 운송장 입력시
            return '배송중'
        else:
            return '구매확정'

    def get_name(self, obj):
        trades = obj.trade_set.all()
        if trades.count() > 1:
            name = trades.first().product.name + ' 외 ' + str(trades.count()-1) + '건'
        else:
            name = trades.first().product.name
        return name

    def get_thumbnail(self, obj):
        trade = obj.trade_set.first()
        thumbnail_url = trade.product.prodthumbnail.image_url
        return thumbnail_url

    def get_condition(self, obj):
        status = obj.status
        completed_date = obj.delivery.number_created_time
        if status in [13, 2, 3, 4]: # review 작성 전 + 운송장 입력 관련
            if not completed_date: # 수령확인 안됨(리뷰 없음) -> 운송장 입력일로부터 5일 지났을 경우
                return 0
            if completed_date + timedelta(days=5) < datetime.now():  # 5일 이후
                return 1  # 리뷰작성 버튼
            else:  # 5일 이전
                return 0  # 수령확인 버튼
        elif status in [5, 6]: # 리뷰가 생성되었을 때 5, -> 별점만 남기거나(수령확인) + 리뷰까지 남긴 경우
            if hasattr(obj, 'review'):
                if not obj.review.context: # 리뷰는 있지만, 내용이 없는 경우 : 별점만 준 경우 (수령확인 시)
                    return 1 # 리뷰작성
                return 2 # None : 수령확인시 리뷰를 작성했거나, 리뷰작성 버튼을 눌러 리뷰 글이 있는 경우
            else:
                return 9
        return 3 # 기타


class SoldDealSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    condition = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = ['id', 'status', 'name', 'total', 'thumbnail', 'condition']

    def get_status(self, obj):
        if obj.status == 2:
            return '결제완료'
        elif obj.status in [3, 4]:
            return '배송중'
        else:
            return '거래완료'

    def get_name(self, obj):
        trades = obj.trade_set.all()
        if trades.count() > 1:
            name = trades.first().product.name + ' 외 ' + str(trades.count()-1) + '건'
        else:
            name = trades.first().product.name
        return name

    def get_thumbnail(self, obj):
        trade = obj.trade_set.first()
        if hasattr(trade, 'product'):
            thumbnail_url = trade.product.prodthumbnail.image_url
            return thumbnail_url
        return ''

    def get_condition(self, obj):
        delivery = obj.delivery
        if delivery.state == 'step0':
            return 0 # 입력완료
        return 1 # 운송장 입력 필요


class ReviewSerializer(serializers.ModelSerializer):
    buyer = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Review
        fields = ['buyer', 'seller', 'deal', 'context', 'satisfaction', 'deal', 'thumbnail']


class ReviewRetrieveSerializer(serializers.ModelSerializer):
    deal_thumbnail = serializers.SerializerMethodField()
    satisfaction = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['deal_thumbnail', 'satisfaction']

    def get_deal_thumbnail(self, obj):
        trade = obj.deal.trade_set.first()
        thumbnail_url = trade.product.prodthumbnail.image_url
        return thumbnail_url

    def get_satisfaction(self, obj):
        satisfaction = float(obj.satisfaction)
        return satisfaction


class SimpleWaybillSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = ['code', 'number']

    def get_code(self, obj):
        code = obj.get_code_display()
        return code


class WaybillCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ['code', 'number']
