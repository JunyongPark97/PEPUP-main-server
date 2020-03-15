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
        elif obj.status in [3, 4]:
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
        if status in [13, 2, 3, 4]: # review 작성 전 or 운송장 입력일로부터 5일 이내
            # 수령확인 버튼
            return 0
        elif status in [5, 6]:
            # 리뷰작성 버튼(수령확인은 되었지만(클릭 or 5일자동), 리뷰 글이 없거나 자동수령이 되어 리뷰 자체가 없는 경우)
            if hasattr(obj, 'review'):
                # 리뷰는 있지만, 내용이 없는 경우 : 별점만 준 경우 (수령확인 시)
                if not obj.review.context:
                    return 1 # 리뷰작성
                return 2 # None : 수령확인시 리뷰를 작성했거나, 리뷰작성 버튼을 눌러 리뷰 글이 있는 경우
            else:
                return 1 # 리뷰작성: 자동 수령확인이 되어 리뷰 자체가 없는 경우
        return 3 # 기타


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
