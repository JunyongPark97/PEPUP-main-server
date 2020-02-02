from django.db import models
from django.conf import settings
from ckeditor_uploader.fields import RichTextUploadingField


class FAQ(models.Model):
    """
    자주 묻는 질문/답변입니다.
    """
    APP_FUNC = 2
    APP_ERR = 3
    ORDERING = 4
    REFUND = 5
    OTHERS = 10
    ALL = 1
    GROUP_CHOICES = (
        (APP_FUNC, '앱 기능 관련'),
        (APP_ERR, '오류 관련'),
        (ORDERING, '주문 배송 관련'),
        (REFUND, '환불'),
        (OTHERS, '기타'),
        (ALL, '전체'),
    )

    title = models.CharField(max_length=40)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    group = models.IntegerField(choices=GROUP_CHOICES, default=99)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name_plural = '자주묻는 질문'


class Notice(models.Model):
    """
    공지사항 모델입니다.
    """
    title = models.CharField(max_length=40, help_text="this field is title")
    content = RichTextUploadingField(help_text="rich_text_field로 이미지 등을 추가할 수 있습니다.")
    important = models.BooleanField(default=False, help_text="true일 경우 앱내 상단에 강조되어 표시됩니다.")
    hidden = models.BooleanField(default=False, help_text="true일 경우 공지 리스트에서 보이지 않습니다.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name_plural = '공지사항'


class Official(models.Model):
    """
    이용약관, 개인정보처방침에 관한 모델입니다.
    """
    USE_TERM = 0
    PERSONAL_INFORMATION_USE_TERM = 1
    COMPANY_INFO = 2
    TYPES = (
        (USE_TERM, 'Use Term'),
        (PERSONAL_INFORMATION_USE_TERM, 'Personal Infromation Use Term'),
        (COMPANY_INFO, 'Company Introduce'),
    )
    official_type = models.IntegerField(choices=TYPES)
    version = models.IntegerField(default=0)
    content = RichTextUploadingField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'[VER=%d] %s' % (self.version, self.get_official_type_display())

    class Meta:
        ordering = ['-version']
        verbose_name_plural = '약관'