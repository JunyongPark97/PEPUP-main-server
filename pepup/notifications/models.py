import jsonfield as jsonfield
from django.db import models
from django.conf import settings
from fcm_django.models import AbstractFCMDevice

MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

DAYS_OF_WEEK = [
    (MONDAY, 'Monday'),
    (TUESDAY, 'Tuesday'),
    (WEDNESDAY, 'Wednesday'),
    (THURSDAY, 'Thursday'),
    (FRIDAY, 'Friday'),
    (SATURDAY, 'Saturday'),
    (SUNDAY, 'Sunday'),
]


class FCMDevice(AbstractFCMDevice):
    """
    FCMDevice라는 모델을 생성했습니다. fcm-django 에서는 model에 user가 물려있지 않아서 새롭게 정의했습니다.
    해당 모델 안에 유저와, 유저에게 푸쉬 보낼 떄 필요한 endpoint arn 이 정의되어 있습니다.
    """
    DEVICES = [
        (1, 'ANDROID'),
        (2, 'IOS'),
        (3, 'CHROME'),
    ]

    device_type = models.IntegerField(choices=DEVICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    endpoint_arn = models.CharField(max_length=150, blank=True, help_text='aws sns message publish용 arn입니다.')


def get_choices():
    from notifications.types import action_types
    return action_types


class Notification(models.Model):
    """
    notifications 모델입니다.
    notifications 모델 생성 후, fcm을 사용하여(android, ios) push msg를 보내게 됩니다.
    1. notifications 모델 생성
    2. 수신할 user들에 대한 NotificationUserLog model 생성
    3. send_async_push
    """
    action = models.IntegerField(choices=get_choices(), db_index=True,
                                 help_text="해당 notification의 종류를 의미합니다.")
    target = models.IntegerField(null=True, blank=True, help_text="대상을 의미합니다. 공지사항 푸쉬의 경우 id, 문제 관련 푸쉬의 경우 마찬가지로 id")
    title = models.CharField(max_length=30, null=True, blank=True, help_text="제목입니다.")
    content = models.CharField(max_length=100, null=True, blank=True, help_text="내용입니다.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, help_text="DEPRECATED 2017.8.31")
    image = models.TextField(blank=True, null=True, help_text="프로필 이미지 등 push msg에 사용되는 큰 아이콘")
    icon = models.TextField(blank=True, null=True, help_text="작은 아이콘 이미지")
    link = models.TextField(blank=True, null=True, help_text="딥링크 주소")
    big_image = models.TextField(blank=True, null=True, help_text="큰 이미지 notification에 사용합니다.")

    class Meta:
        verbose_name_plural = 'Push 알림'
        ordering = ['-created_at']

    def __unicode__(self):
        if hasattr(self, 'user_logs'):
            logs = self.user_logs.filter(read_at__isnull=False)
            delta = 0
            for lo in logs:
                delta = delta + (lo.read_at - lo.notification.created_at).total_seconds()
            return u'%d (action = %d, title : %s) 보냄 : %d명, 읽음 : %d명, 평균 읽음 시간(초) : %d' % (
            self.id, self.action, self.title, self.user_logs.all().count(),
            self.user_logs.filter(read_at__isnull=False).count(), delta)
        else:
            return u'%d (action = %d) %s' % (self.id, self.action, self.title)

    @property
    def is_readable(self):
        try:
            from notifications.types import notification_types
            return notification_types[self.action].is_readable
        except:
            return False

    @property
    def is_notifiable(self):
        try:
            from notifications.types import notification_types
            return notification_types[self.action].is_notifiable
        except:
            return False


class NotificationUserLog(models.Model):
    """
    각 Notification에 대한 User의 읽음, 지움 등을 표시한 모델 이 모델이 생성되면 user에게 push가 발송되었다고 볼 수 있다.
    """
    notification = models.ForeignKey(Notification, related_name="user_logs", on_delete=models.CASCADE)
    read_at = models.DateTimeField(blank=True, null=True, help_text="유저가 해당 메시지를 읽었다면 null이 아니게 됩니다.")
    deleted_at = models.DateTimeField(blank=True, null=True,
                                      help_text="해당 푸쉬가 보여서는 안될 종류의 것이라면 생성과 동시에 auto_now_add 유저가 해당 메시지를 지웠다면 null이 아니게 됩니다.")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notification_logs")
    extras = jsonfield.JSONField(null=True, blank=True, help_text="json형식으로 추가 정보를 전달할 때 사용합니다.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True, null=True)

    def __unicode__(self):
        return u'{}:{}:{}:{}'.format(self.notification.action, self.user.social_default_nickname, self.notification.title,
                                     self.notification.content)


class ReservedNotification(models.Model):
    """
    예약 notification 으로 cron 에 의해서 각 reserved_at 으로 등록된 시간에 notification 이 전송되는 모델.

    status 는 2018.6.12 일 이후에 추가된 필드로 해당 예약 notification 의 상태를 나타내기위해서 사용되고,
    만약 push_reserved_notification() 호출시에 undeterministic behavior 가 발생하는 상황을 개선하기 위해 추가되었습니다.
    실제 push 발송전에는 wating 상태이고, push_reserved_notification() 를 통해서 발송이 되면 각각 sending, sent 상태로 변경됩니다.

    status 의 변경이 발생하는 지점들
    1. WAITING
    - create_reserved_notification() 실행시 초기값으로 세팅.
    2. SENDING
    - push_reserved_notification() 실행시 전송가능할때 변경.
    3. SENT
    - send_push_async() 실행완료후에 변경.
    4. ALREADY_USE_FREE_QUESTION, ALREADY_SEARCH_OCR, ALREADY_OTHER_NOTIFICATION
    - push_reserved_notification() 실행시 전송이 가능하지 않을때 변경.

    """
    WAITING = 1
    SENDING = 2
    SENT = 3
    ALREADY_USE_FREE_QUESTION = 10
    ALREADY_SEARCH_OCR = 11
    ALREADY_OTHER_NOTIFICATION = 12

    STATUS_LIST = (
        (WAITING, 'waiting'),
        (SENDING, 'sending'),
        (SENT, 'sent'),
        (ALREADY_USE_FREE_QUESTION, 'already free_question'),
        (ALREADY_SEARCH_OCR, 'already search_ocr'),
        (ALREADY_OTHER_NOTIFICATION, 'already other_notification'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reserved_notifications")
    notification = models.ForeignKey(Notification, related_name="reserved_notifications")

    # TODO : target 에 대한 정확한 명시가 필요 : 첫 구매 안해본사람, 처음 옷 등록해본 사람, 첫 구매 해본사람 등
    target_notification = models.ForeignKey(TargetNotification, related_name="reserved_notifications")
    reason = models.CharField('이유', max_length=100, null=True, blank=True, help_text="어떻게 이렇게 보내지는가?")
    goal = models.TextField('목표 달성 상태', null=True, blank=True, help_text='target_notification 의 목표 도달했는지 측정')
    status = models.IntegerField('전송상태', choices=STATUS_LIST, blank=True, null=True)
    reserved_at = models.DateTimeField(help_text='notification 이 전송되는 예약 시간')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name_plural = '예약 Notification'

    def __unicode__(self):
        reserved_notification = u'{}] {}'.format(self.id, self.user)
        return reserved_notification


# 요일을 many to many 로 넣기.
class Days(models.Model):
    day = models.IntegerField('요일', choices=DAYS_OF_WEEK, null=True, blank=True)

    class Meta:
        verbose_name_plural = '일주일 요일'

    def __unicode__(self):
        return self.get_days_of_week()

    def get_days_of_week(self):
        days_of_week = ''
        if self.day is not None:
            days_of_week = dict(DAYS_OF_WEEK).get(self.day)
        return days_of_week
