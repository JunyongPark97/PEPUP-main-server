from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework.reverse import reverse

action_types = []
use_action_types = []

# Notification Action 값으로 NotificationType모델을 접근하기 위한
notification_types = {}


def NotificationType(_class):
    action_types.append((_class.action, _class.__name__))
    notification_types[_class.action] = _class
    return _class


def NotificationButtonUseType(_class):
    use_action_types.append(_class.action)
    return _class

"""
1. B가 나를(a) 타인이 나를 팔로우 했을 때 // 홈페이지로 or 그 사람 프로필로
2. B가 나의 물건을 구매함 // 운송장 번호 입력하는 페이지
3. B가 2의 결제를 취소함 // 판매내역 페이지로 이동 -> 여기서 상품 페이지로 이동(client)
4. (b입장에서) a가 물건을 발송함 // b 에게 알림(구매 페이지)
5. (b 입장에서) a가 보낸 물건이 배송완료됨 + 24이내 환불 등 + 리뷰 요청 // 구매한 상품 페이지
6. c:또다른 내가 팔로우한 사람 : 이 상품을 업로드 시작 함 (24시간에 한번)로 // 그 사람 프로필로? 홈페이지로?
7. 공지사항
8. 새로운 상품이 +100개 입고됐어요
9.

"""
class BaseNotificationType:
    """
    기본 푸쉬 메시지 세팅
    """

    def __init__(self, list_user):
        self.list_user = list_user

    class Meta:
        abstract = True

    action = None
    is_readable = False  # 리스트에 저장하는가
    is_notifiable = False  # 모든 push는 보내지만, user에게 pop시키지 않는 것들이 있음 push message를 유저에게 표시하는가(list와 별개로 휴대폰 푸쉬)

    def title(self):
        return ""

    def content(self):
        return ""

    def image(self):
        return ""

    def icon(self):
        return ""

    def link(self):
        return "mypepup.com/"

    def extras(self):
        return {}

    def big_image(self):
        return None

    def target(self):
        return None

    def get_notification(self):
        from notifications.models import Notification
        noti = Notification.objects.create(
            action=self.action,
            target=self.target(),
            title=self.title(),
            content=self.content(),
            image=self.image(),
            icon=self.icon(),
            big_image=self.big_image(),
            link=self.link()
        )
        return noti

    def send(self):
        from notifications.tools import send_push_async
        send_push_async(list_user=self.list_user, notification=self.get_notification(),
                        extras=self.extras())


@NotificationType
class RootMessage(BaseNotificationType):
    """
    가입을 하지 않아도 받을 수 있는 푸쉬 메시지
    """
    action = 1
    is_readable = False
    is_notifiable = True


@NotificationType
class UserNotice(BaseNotificationType):
    """
    모든 유저에게 발송하는 공통적인 공지 푸쉬 메세지
    """
    action = 101
    is_readable = True
    is_notifiable = True

    def __init__(self, notice, list_user):
        self.notice = notice
        super(UserNotice, self).__init__(list_user)

    def title(self):
        return _("notifications_new_noti")

    def content(self):
        return self.notice.title

    def image(self):
        return ""

    def link(self):
        return "mypepup.com/api/notice/{}/".format(self.notice.id)

    def target(self):
        return self.notice.id


@NotificationType
class UserEventNotice(BaseNotificationType):
    """
    모든 유저에게 발송하는 공통적인 이벤트 푸쉬 메세지
    """
    action = 102
    is_readable = True
    is_notifiable = True

    def __init__(self, event_notice, list_user):
        self.event_notice = event_notice
        super(UserEventNotice, self).__init__(list_user)

    def title(self):
        return _('notification_new_event')

    def content(self):
        return self.event_notice.title

    def image(self):
        return ""

    def link(self):
        return "mypepup.com/api/event/{}/".format(self.event_notice.id)

    def target(self):
        return self.event_notice.id


@NotificationType
class UserMainDaily(BaseNotificationType):
    """
    Target User 를 이용하여 사용자에게 예약 notification 이 도착하는 메시지.
    매일 한개만 생성이되고 동일한 notification 이면 이것 한개만을 공유하여서 사용한다.
    """
    action = 103
    is_readable = True
    is_notifiable = True

    def __init__(self, _title, _content, user_list=None):
        self._title = _title
        self._content = _content
        super(UserMainDaily, self).__init__(user_list)

    def title(self):
        return self._title

    def content(self):
        return self._content

    def icon(self):
        return ""

    def image(self):
        return ''

    def link(self):
        return "mypepup.com/api/products/"

    def target(self):
        return None


@NotificationType
class UserReservedMain(BaseNotificationType):
    """
    Target User 를 이용하여 학생에게 예약 notification 이 도착하는 메시지
    """
    action = 104
    is_readable = True
    is_notifiable = True

    def __init__(self, _title, _content, user_list=None):
        self._title = _title
        self._content = _content
        super(UserReservedMain, self).__init__(user_list)

    def title(self):
        return self._title

    def content(self):
        return self._content

    def icon(self):
        return ""

    def image(self):
        return ''

    def link(self):
        return "mypepup.com/api/products/"

    def target(self):
        return None



@NotificationType
class UserRetentionNotification(BaseNotificationType):
    """
    retention notification 만을 확인하기 위해서 생성한 notification
    """
    action = 105
    is_readable = True
    is_notifiable = True

    def __init__(self, _title, _content, user_list=None):
        self._title = _title
        self._content = _content
        super(UserRetentionNotification, self).__init__(user_list)

    def title(self):
        return self._title

    def content(self):
        return self._content

    def image(self):
        return ''

    def link(self):
        return "mypepup.com/api/products/"

    def target(self):
        return None


@NotificationType
class UserFollowUser(BaseNotificationType):
    """
    유저가 유저를 팔로우 했을 때 발송하는 푸쉬 메세지
    """
    action = 200
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, from_user, to_user):
        self.from_user = from_user
        self.to_user = to_user
        super(UserFollowUser, self).__init__(list_user)

    def title(self):
        return _('notification_user_follow_user_title').format(
            self.from_user.social_default_nickname)

    def content(self):
        return _('notification_user_follow_user_content')

    def image(self):
        try:
            return self.from_user.profile_image.image_key.url # TODO : 확정되면 수정하기.
        except:
            pass
        return super(UserFollowUser, self).image()

    def link(self):
        try:
            return "mypepup.com/api/followList/{}/".format(self.to_user.id) # TODO : 내 팔로워 목록으로 이동해야함. 아직 api 안나옴.
        except:
            return "mypepup.com/api/products/"

    def extras(self):
        if self.from_user.social_default_nickname:
            return {"nickname": self.from_user.social_default_nickname}
        else:
            super(UserFollowUser, self).extras()

    def target(self):
        return self.from_user.id # TODO : 사용처 미정.


@NotificationType
class UserNewAnswer(BaseNotificationType):
    """
    유저가 유저에게 답변이 도착하면 오는 메시지
    """
    action = 201
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, chat):
        self.speaker = chat.speaker
        self.listener = chat.listener
        self.chat_room = chat
        super(UserNewAnswer, self).__init__(list_user)

    def title(self):
        return _('notification_user_new_answer_title').format(self.speaker.social_default_nickname)

    def content(self):
        return _('notification_user_new_answer_content')

    def image(self):
        try:
            return self.speaker.profile_image.image_key.url
        except:
            pass
        return super(UserNewAnswer, self).image()

    def link(self):
        try:
            return "mypepup.com/chat/?chatRoomUrl={}".format(self.chat_room.websocket_url)
        except:
            return "mypepup.com/api/products/"

    def extras(self):
        try:
            return {"nickname": self.speaker.social_default_nickname}
        except:
            super(UserNewAnswer, self).extras()

    def target(self):
        return self.chat_room.id


@NotificationType
class UserProductSold(BaseNotificationType):
    """
    결제했을 때 셀러에게 보내는 푸쉬 / 운송장 번호 입력하는 곳(판매상품관리 페이지로 이동해야함)
    Deal 별로 알림 가야 함. 운송장 번호 입력하는 곳으로 갈 수 있음.
    """
    action = 202
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, deal):
        self.deal = deal
        super(UserProductSold, self).__init__(list_user)

    def title(self):
        return _('notification_user_product_sold_title')

    def content(self):
        return _('notification_user_product_sold_content')

    def image(self):
        return ""

    def link(self):
        return "mypepup.com/api/deal/{}".format(self.deal.id) # TODO : 아직 해당 api 가 안나옴.

    def target(self):
        return self.deal.id


@NotificationType
class BuyerCanceledPayment(BaseNotificationType):
    """
    구매자가 결제 취소했을 떄 보내는 푸쉬
    Payment 의 status 가 결제 취소로 update 되면, 해당 Payment의 Deal 의 각 셀러에게 알림을 보내야 함.
    * 결제 취소했을 때 어디로 보낼지 기획 미정
    """
    action = 203
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, deal):
        self.deal = deal
        super(BuyerCanceledPayment, self).__init__(list_user)

    def title(self):
        return _('notification_user_canceled_payment_title')

    def content(self):
        return _('notification_user_canceled_payment_content')

    def image(self):
        return ""

    def link(self):
        return "mypepup.com/api/deal/{}/?canceled=true".format(self.deal.id) # TODO : parameter로 할지 미정

    def target(self):
        return self.deal.id


@NotificationType
class SellerRegisterWaybill(BaseNotificationType):
    """
    판매자가 운송장 번호를 등록했을 때 보내는 푸쉬
    """
    action = 204
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, deal):
        self.deal = deal
        self.seller = deal.seller
        super(SellerRegisterWaybill, self).__init__(list_user)

    def title(self):
        return _('notification_user_register_waybill_title')

    def content(self):
        return _('notification_user_register_waybill_content').format(
            self.seller.social_default_nickname) # TODO : jun 형과 모델 구체화 후 확정.

    def image(self):
        try:
            return self.seller.profile_image.image_key.url
        except:
            pass
        return super(SellerRegisterWaybill, self).image()

    def link(self):
        return "mypepup.com/api/deal/{}/".format(self.deal.id)

    def target(self):
        return self.deal.id


@NotificationType
class BuyerRegisterReview(BaseNotificationType):
    """
    구매자가 리뷰를 남겼을 때 판매자에게 보내는 푸쉬 알림 (구매확정 연동)/
    """
    action = 205
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, review):
        self.review = review
        super(BuyerRegisterReview, self).__init__(list_user)

    def title(self):
        return _('notification_buyer_register_review_title')

    def content(self):
        return _('notification_buyer_register_review_content')

    def link(self):
        try:
            return "mypepup.com/api/products/{}/".format(self.review.product.id)
        except:
            return "mypepup.com/api/products/"

    def target(self):
        return self.review.id


@NotificationType
class AutoConfirmPurchase(BaseNotificationType):
    """
    자동구매확정이 되었을 때 셀러에게 보내는 푸쉬
    trade (상품) 별로 구매확정 알림.
    """
    action = 206
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, trade):
        self.trade = trade
        super(AutoConfirmPurchase, self).__init__(list_user)

    def title(self):
        return _('notification_buyer_register_review_title')

    def content(self):
        return _('notification_buyer_register_review_content')

    def link(self):
        try:
            return "mypepup.com/api/trades/{}/".format(self.trade.id)
        except:
            return "mypepup.com/api/trades/"

    def target(self):
        return self.trade.id


@NotificationType
class ProductDeliveryFinish(BaseNotificationType):
    """
    [보류]
    배송 완료시 리뷰 작성 푸쉬 알림 // 아직 배송완료 정보를 알 수 있는 방법이 현재는 없음
    """
    action = 207
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, product):
        self.product = product
        super(ProductDeliveryFinish, self).__init__(list_user)

    def title(self):
        return _('notification_product_delivery_finish_title')

    def content(self):
        return _('notification_product_delivery_finish_content')

    def link(self):
        return "".format(self.product.id)

    def target(self):
        return self.product.id


@NotificationType
class SellerStartUpload(BaseNotificationType):
    """
    [보류]
    팔로우한 샵이 업로드를 시작했을 때 06:00AM 기준으로 하루에 한번 푸쉬알림
    """
    action = 208
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, product):
        self.product = product
        super(SellerStartUpload, self).__init__(list_user)

    def title(self):
        return _('notification_seller_start_upload_title')

    def content(self):
        return _('notification_seller_start_upload_content')

    def link(self):
        try:
            return "mypepup.com/api/products/{}/".format(self.product.id)
        except:
            return "mypepup.com/api/products/"

    def target(self):
        return self.product.id


@NotificationType
class ConfirmPurchaseLimitAlmostOver(BaseNotificationType):
    """
    자동 구매확정 2일 전 리뷰 재촉 푸쉬 (결제 3일 후)
    Deal 별로 알림, Deal 중 리뷰 안남긴 Trade 들 개수와 함께 알림
    """
    action = 301
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, deal):
        self.deal = deal
        super(ConfirmPurchaseLimitAlmostOver, self).__init__(list_user)

    def title(self):
        return _('notification_confirm_purchase_limit_almost_over_title')

    def content(self):
        return _('notification_confirm_purchase_limit_almost_over_title')

    def link(self):
        return "mypepup.com/api/deak/{}/".format(self.deal.id) # TODO : 구매목록 api로 바꿔야 함

    def image(self):
        return ""


@NotificationType
class UserPaymentResult(BaseNotificationType):
    """
    결제 완료 푸쉬 클릭하면 결제내역 모바일 웹을 앱내에서 보여준다
    """
    action = 302
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, payment):
        self.payment = payment
        super(UserPaymentResult, self).__init__(list_user)

    def title(self):
        return _('notification_user_payment_result_title')

    def content(self):
        return _('notification_user_payment_result_content')

    def link(self):
        return "mypepup.com/api/[보류]"

    def extras(self):
        try:
            return {"product_name": self.payment.deal_set.first().trade_set.first().product.name}
        except:
            return super(UserPaymentResult, self).extras()

    def target(self):
        return self.order.id


@NotificationType
class UserContactReply(BaseNotificationType):
    """
    문의하기에 무언가 달렸을 때 받는 푸쉬
    """
    action = 401
    is_readable = True
    is_notifiable = True

    def __init__(self, list_user, contact, contactreply):
        self.contact = contact
        self.contactreply = contactreply
        super(UserContactReply, self).__init__(list_user)

    def title(self):
        return _('notification_user_contact_reply_title')

    def content(self):
        return self.contactreply.content

    def image(self):
        try:
            return self.contactreply.author.social_default_profile_image_url
        except:
            super(UserContactReply, self).extras()

    def link(self):
        return "mypepup.com/api/contact/{}/".format(self.contact.id)

    def extras(self):
        try:
            return {"nickname": self.contactreply.author.social_default_nickname}
        except:
            super(UserContactReply, self).extras()

    def target(self):
        return self.contact.id
