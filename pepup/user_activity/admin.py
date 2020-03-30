from django.contrib import admin

from user_activity.models import UserActivityLog


class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'content']


admin.site.register(UserActivityLog, UserActivityLogAdmin)
