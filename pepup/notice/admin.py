from django.contrib import admin
from .models import Notice, Official, FAQ, NoticeBanner


# Register your models here.


class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title','pk','important','hidden', 'created_at', 'updated_at']


class NoticeBannerAdmin(admin.ModelAdmin):
    list_display = ['title','pk','hidden', 'created_at', 'updated_at']


class OfficialAdmin(admin.ModelAdmin):
    list_display = ['official_type','pk','version', 'created_at', 'updated_at']


class FAQAdmin(admin.ModelAdmin):
    list_display = ['group_name','pk','title', 'created_at', 'updated_at']

    # def get_ordering(self, obj):
    #     return obj.group

    def group_name(self, obj):
        return obj.get_group_display()


admin.site.register(Notice,NoticeAdmin)
admin.site.register(NoticeBanner,NoticeBannerAdmin)

admin.site.register(Official, OfficialAdmin)
admin.site.register(FAQ, FAQAdmin)
