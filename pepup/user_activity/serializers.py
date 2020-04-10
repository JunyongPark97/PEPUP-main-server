from datetime import timedelta, datetime
from django.utils.timesince import timesince
from rest_framework import serializers
from payment.models import Deal, Review, Delivery, Trade
from user_activity.models import UserActivityLog


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


class ActivityProductThumbnailSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = ['image_url']

    def get_image_url(self, obj):
        thumbnail = obj.product.prodthumbnail
        return thumbnail.image_url


class ActivitySerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    big_image_url = serializers.SerializerMethodField()
    product_image_url = serializers.SerializerMethodField()
    redirectable = serializers.SerializerMethodField()
    redirect_id = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    condition = serializers.SerializerMethodField()
    deep_link = serializers.SerializerMethodField()
    obj_id = serializers.SerializerMethodField()

    class Meta:
        model = UserActivityLog
        fields = ['id', 'content', 'age', 'big_image_url', 'product_image_url',
                  'condition', 'redirectable', 'redirect_id', 'deep_link', 'obj_id']

    def _condition(self, obj):
        """
        :return: about, status, redirectable, redirect_id, obj_id
        """
        status = obj.status
        if status in [100, 101, 102, 190, 200, 201, 202]:  # 구매,판매관련
            deal = obj.reference.deal

            # buyer
            if status == 100:
                return status, 0, False, None, None # status 0 : None
            elif status == 101:
                if hasattr(deal, 'review'):
                    if deal.review.context:
                        return status, 1, False, None, deal.id  # status 1 리뷰 존재 : None(review 작성완료),
                    return status, 11, False, None, deal.id # status 11 별점만 있음 : 리뷰 작성 btn
                return status, 10, False, None, deal.id # status 10 수령확인 btn
            elif status == 102: # 운송장 작성 이후 5일 뒤 자동생성
                if hasattr(deal, 'review'):
                    return status, 1, False, None, deal.id  # None(review 작성완료)
                return status, 11, False, None, deal.id  # 5일 뒤 자동구매 확정 이후 리뷰 없는경우: 리뷰작성 btn
            elif status == 190:
                return status, 99, False, None, None # 결제에러 error status 99

            # seller
            elif status == 200:
                if deal.delivery.number_created_time:
                    return status, 2, False, None, deal.id  # 운송장 입력 완료: None(운송장입력완료)
                return status, 3, False, None, deal.id  # 운송장 없음 : 운송장 입력 btn
            elif status in [201, 202, 203]:
                return status, 0, False, None, None  # None

            else:
                return 999, -1, False, None, None  # None(error)

        # other
        elif status in [3, 4, 5, 6, 7]:
            return status, 0, False, None, None
        else:
            return 999, -1, False, None, None  # None(error)

    # get name for payment activity
    def _product_name(self, obj):
        trades = obj.trade_set.all()
        if trades.count() > 1:
            name = trades.first().product.name + ' 외 ' + str(trades.count()-1) + '건'
        else:
            name = trades.first().product.name
        return name

    # return condition
    def get_condition(self, obj):
        _, condition, _, _, _ = self._condition(obj)
        return condition

    # return redirectable
    def get_redirectable(self, obj):
        _, _, redirectable, _, _ = self._condition(obj)
        return redirectable

    # return redirect id
    def get_redirect_id(self, obj):
        _, _, _, redirect_id, _ = self._condition(obj)
        return redirect_id

    def get_deep_link(self, obj):
        return None

    def get_obj_id(self, obj):
        _, _, _, _, obj_id = self._condition(obj)
        return obj_id

    def get_age(self, obj):
        now = datetime.now()
        created_at = obj.created_at
        try:
            diff = now - created_at
        except:
            return created_at
        if diff <= timedelta(minutes=1):
            return 'just now'
        elif diff >= timedelta(days=1):
            return created_at.strftime('%Y.%m.%d')
        return '%(time)s ago' % {'time': timesince(created_at).split(', ')[0]}

    # return image urls for payment activity
    def get_product_image_url(self, obj):
        about, condition, _, _, _ = self._condition(obj)
        if not about in [100, 101, 102, 190, 200, 201, 202]:
            return None
        deal = obj.reference.deal
        trades = deal.trade_set.all()
        return ActivityProductThumbnailSerializer(trades, many=True).data

    # return big image url
    def get_big_image_url(self, obj):
        about, condition, _, _, _ = self._condition(obj)
        # TODO : notice image
        pepup_image = 'https://pepup-server-storages.s3.ap-northeast-2.amazonaws.com/media/pepup.png'
        if about == 100:
            return pepup_image
        elif about == 101:
            if condition == 10:
                profile = obj.reference.deal.seller.profile
                return profile.profile_img_url
            else:
                return pepup_image
        elif about == 102:
            return pepup_image
        elif about == 190: # TODO : error image 로 대체해야함
            return pepup_image

        elif about == 200:
            if condition == 2:
                return pepup_image
            profile = obj.reference.deal.buyer.profile
            return profile.profile_img_url
        elif about == 201:
            profile = obj.reference.deal.buyer.profile
            return profile.profile_img_url
        elif about == 202:
            profile = obj.reference.deal.buyer.profile
            return profile.profile_img_url
        elif about == 203:
            return pepup_image

        else: # TODO : follow, tag ...
            return pepup_image

    # return content
    def get_content(self, obj):
        about, condition, _, _, _ = self._condition(obj)
        try:
            name = self._product_name(obj.reference.deal)
        except:
            name = None

        if about == 100:
            return '\'{}\' 결제가 완료되었습니다.'.format(name)
        elif about == 101:
            if condition == 10:
                return '주문하신 상품 \'{}\' 배송되었습니다. \n 배송이 완료되었다면 수령확인 해 주세요.'.format(name)
            elif condition == 11:
                return '거래가 완료되었습니다. \n 구매를 망설이는 다른분들을 위해 이제 리뷰를 남겨볼까요?'
            elif condition == 1:
                return '리뷰 남기기 완료!'
        elif about == 102:
            if condition == 11:
                return '\'{}\' 자동 구매 확정이 되었습니다. \n 이제 거래에 대해 간단한 리뷰 남겨 볼까요?'.format(name)
            elif condition == 1:
                return '리뷰 남기기 완료!'
        elif about == 190:
            return '결제 오류로 거래가 취소되었습니다.'

        elif about == 200:
            if condition == 2:
                return '\'{}\' 운송장 입력이 완료되었습니다.'.format(name)
            elif condition == 3:
                return '\'{}\' 주문되었습니다. \n 상품을 기다리는 구매자를 위해 운송장 번호를 입력해 주세요!'.format(name)
        elif about == 201:
            deal = obj.reference.deal
            if deal.review.context:
                return '\'{}\' 거래가 완료되었습니다. {}\'님이 남기신 리뷰가 있습니다.'.format(name, deal.buyer.nickname)
            return '\'{}\' 거래가 완료되었습니다.'.format(name)
        elif about == 202:
            return '\'{}\' 자동 거래 완료되었습니다.'.format(name)
        elif about == 203:
            return '\'{}\' 정산 완료 되었습니다.'.format(name)

        elif about == 3:
            # TODO : how to make it?
            return '관심있는 태그 \'{}\' 상품이 등록되었습니다.'.format(None)
        elif about == 4:
            return ''
        elif about == 5:
            # TODO
            return '누군가가 나를 팔로우 했습니다.'
        elif about in [6,7]:
            return ''



