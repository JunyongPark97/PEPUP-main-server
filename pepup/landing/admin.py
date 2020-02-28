from django.contrib import admin
from landing.models import Register
from datetime import datetime


class RegisterAdmin(admin.ModelAdmin):
    list_display = ['name','phone','quantity', 'check', 'manager', 'bank', 'account', 'register_time']
    search_fields = ('name', 'phone', 'bank', 'account')
    list_editable = ('check', 'manager')
    ordering = ('-created_at',)

    def register_time(self, obj):
        time = obj.created_at
        re_time = datetime.strftime(time, '%Y-%m-%d %H:%M')
        return re_time


admin.site.register(Register, RegisterAdmin)