# -*- encoding: utf-8 -*-
import json
import random
from django.utils import timezone


from logs.models import UserAccessLog
from datetime import timedelta, datetime, time
from core.aws.clients import lambda_client
from notifications.models import Notification, NotificationUserLog, ReservedNotification, Days
from notifications.serializers import NotificationSerializer
from notifications.types import *
from pytz import timezone as pytz_timezone
from django.utils.translation import ugettext_lazy as _, activate


STUDENT = 1
TEACHER = 2
seoul_tz = pytz_timezone('Asia/Seoul')


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def _push_android(endpoints, notification):
    serializers = NotificationSerializer(notification)
    try:
        serializer_data = serializers.data
    except Exception as e:
        serializer_data = None

    if serializer_data:
        for sliced_endpoints in batch(endpoints, 100):
            data = {
                "action": notification.action,
                "param": serializer_data,
                "is_notifiable": notification.is_notifiable,
            }
            gcm_data = {
                "data": data,
                "priority": "high",
            }
            payload = json.dumps({
                "endpoints": sliced_endpoints,
                "gcm_data": gcm_data,
            })
            lambda_client.invoke(FunctionName="NotificationSender",
                                 Payload=payload,
                                 InvocationType='Event')


def _push_ios(endpoints, notification, badge=1):
    serializers = NotificationSerializer(notification)
    try:
        serializer_data = serializers.data
    except Exception as e:
        serializer_data = None

    if serializer_data:
        for sliced_endpoints in batch(endpoints, 100):
            data = {
                "action": notification.action,
                "param": serializer_data,
                "is_notifiable": notification.is_notifiable,
            }
            gcm_data = {
                "data": data,
                "priority": "high",
                "notification": {
                    "title": notification.title.encode(encoding='UTF-8', errors='strict'),
                    "body": notification.content.encode(encoding='UTF-8', errors='strict'),
                    "sound": None,
                    "badge": badge,
                    "content_available": True,
                    "id": 0,
                },
            }
            payload = json.dumps({
                "endpoints": sliced_endpoints,
                "gcm_data": gcm_data,
            })
            lambda_client.invoke(FunctionName="NotificationSender",
                                 Payload=payload,
                                 InvocationType='Event')


def send_push_async(list_user, notification, extras=None, reserved_notification=None):
    from notifications.models import NotificationUserLog
    from notifications.models import FCMDevice
    """
    1. notification model 을 생성합니다. (Notification Type 을 활용합니다.) - on_xxx 방식의 함수에서 요청
    title, content, image, link, is_readable, icon, link, big_image 등등

    2. 해당 notification 에 해당하는 NotificationUserLog 를 bulkcreate 합니다. - send_push_async 에서 처리

    3. 해당 notification 을 해당 user 들에게 send 합니다. - send_push async 에서 처리
    """
    # 1. notification model 을 생성합니다.
    bulk_data = []
    user_ids = []

    if notification.is_readable:
        deleted_at = None
    else:
        deleted_at = timezone.now()

    for user in list_user:
        bulk_data.append(
            NotificationUserLog(user=user, notification=notification, deleted_at=deleted_at,
                                extras=extras))
        user_ids.append(user.id)

    NotificationUserLog.objects.bulk_create(bulk_data)
    device_queryset = FCMDevice.objects.filter(user__in=user_ids).exclude(endpoint_arn='')

    badge = 1
    if len(list_user) == 1:
        badge = NotificationUserLog.objects.filter(user=list_user[0], read_at=None,
                                                   deleted_at=None).distinct().count()

    android_endpoints = device_queryset.filter(device_type=1).values_list('endpoint_arn', flat=True)
    _push_android(android_endpoints, notification)

    ios_endpoints = device_queryset.filter(device_type=2).values_list('endpoint_arn', flat=True)
    _push_ios(ios_endpoints, notification, badge=badge)

    if reserved_notification:
        _update_reserved_notification_status(reserved_notification, ReservedNotification.SENT)


def send_slack(channel, message):
    pass


class NotificationHelper(object):
    """
    action : action값(정수), notifications.models.Notification 참고
    target : action 대상
      (ex) action이 NEW_PAYMENT일 경우, target은 (구매한 상품의) product_id
    user : push 대상 user
    """

    # ACTION 번호 순서로 정리
    # NOTIFICATION START ============================================================================================
    def on_user_notice_create(self, notice):
        # ACTION 101
        from accounts.models import User
        UserNotice(list_user=User.objects.filter(phone_confirm__is_confirmed=True),
                      notice=notice).send()

    def on_user_event_create(self, event_notice):
        # ACTION 102
        from accounts.models import User
        UserEventNotice(list_user=User.objects.filter(phone_confirm__is_confirmed=True),
                           event_notice=event_notice).send()

    def on_user_follow(self, from_user, to_user):
        # from_user : 팔로우 클릭한 사람
        # to_user : from_user가 팔로우 하는 사람
        # ACTION 200
        UserFollowUser(list_user=[to_user], from_user=from_user, to_user=to_user)

    def on_answer(self, chat):
        # ACTION 201
        # Answer모델이 생성또는 업데이트 되면 발송
        UserNewAnswer(list_user=[chat.listener], chat=chat).send()

    def on_product_sold(self, deal):
        # ACTION 202
        # payment(결제) 가 생성되었을 때, Deal 별로 셀러에게 알림.
        UserProductSold(list_user=[deal.seller], deal=deal).send()

    def on_buyer_canceled_payment(self, deal):
        # ACTION 203
        BuyerCanceledPayment(list_user=[deal.seller], deal=deal).send()

    def on_seller_register_waybill(self, deal):
        # ACTION 204
        SellerRegisterWaybill(list_user=[deal.buyer], deal=deal).send()

    def on__buyer_register_review(self, review):
        # ACTION 205
        BuyerRegisterReview(list_user=[review.trade.seller], review=review).send()

    def on_auto_confirm_purchase(self, trade):
        # ACTION 206
        AutoConfirmPurchase(list_user=[trade.seller], trade=trade).send()

    def on_confirm_purchase_limit_almost_over(self, deal):
        # ACTION 301
        ConfirmPurchaseLimitAlmostOver(list_user=[deal.seller], deal=deal).send()

    def on_user_contact_reply(self, student):
        # ACTION 401
        UserContactReply(list_user=[student]).send()

    def on_contactreply(self, contactreply):
        # ACTION 402
        contact = contactreply.contact
        # 질문자의 reply는 slack으로 알림
        if contactreply.author == contact.author:
            if contactreply.image_key:
                text = _('(photo)')
            else:
                text = contactreply.content
            name = contactreply.author.get_full_name()
            message = _('{}_add_contract_reply_{}').format(name, text)
            send_slack('bot_contact', message)
        # 답변자의 reply는 push로 알림
        else:
            if contact.replies.all().count() > 1:
                before_reply = contact.replies.order_by('-id')[1]
                if (before_reply.author.id == contactreply.author.id) and (
                        before_reply.created_at > timezone.now() - timedelta(seconds=300)):
                    return

            UserContactReply(list_user=[contact.author], contactreply=contactreply,
                             contact=contact).send()

    # NOTIFICATION END ==============================================================================================


notification_helper = NotificationHelper()


def get_current_weekday():
    """
    현재 시간에 맞는 요일정보를 가져오기
    :return:
    """
    weekday = timezone.now().astimezone(seoul_tz).weekday()
    return weekday


def get_current_days_of_week():
    """
    현재 시간에 맞는 요일정보를 Days model 에서 가져오기.
    :return:
    """
    day = Days.objects.filter(day=get_current_weekday()).first()
    return day


def make_date_range(date):
    day_min = make_datetime(date, time.min)
    day_max = make_datetime(date, time.max)

    return [day_min, day_max]


def make_datetime(date, pick_time, set_tz=True):
    reserved_at = datetime(date.year, date.month, date.day,
                           pick_time.hour, pick_time.minute, pick_time.second, )
    if set_tz:
        return seoul_tz.localize(reserved_at)
    else:
        return reserved_at


def _check_reserved_notification(reserved_at, user_id=None):
    """
    동일한 날에 예약된 notification 이 있는지 확인한다.
    :param reserved_at: 예약시간
    :param user_id: user_id
    :return:
    """
    reserved_at_min = timezone.make_aware(
        datetime.combine(reserved_at, time.min), seoul_tz)
    reserved_at_max = timezone.make_aware(
        datetime.combine(reserved_at, time.max), seoul_tz)

    notification_list = list(ReservedNotification.objects.values_list('id', flat=True).
                             filter(reserved_at__range=(reserved_at_min, reserved_at_max),
                                    user_id=user_id))

    # 이미 전송된 푸시가 있다면 전송되면 안됨.
    if len(notification_list) > 0:
        return True
    return False


def create_reserved_notification(reserved_at, user=None, user_id=None,
                                 target_notification=None, reason=None,
                                 is_force_create=False):
    """
    notification 이 예약되어 있다면 reserved notification 을 생성시킨다.
    :param is_force_create: 기본적으로 하루에 하나만 생성되지만 강제로 예약 push 가 생성되도록 할지에 대한 여부
    :param reserved_at: 예약날짜
    :param user:
    :param user_id:
    :param target_notification:
    :param reason:
    :return:
    """
    user_id = user.id if user else user_id

    if _check_reserved_notification(reserved_at, user_id=user_id) and not is_force_create:
        return None
    else:
        return ReservedNotification(
            user_id=user_id,
            target_notification=target_notification,
            reason=reason,
            reserved_at=reserved_at,
            status=ReservedNotification.WAITING
        )


def _update_reserved_notification_status(reserved_notification, status):
    reserved_notification.status = status
    reserved_notification.save()
