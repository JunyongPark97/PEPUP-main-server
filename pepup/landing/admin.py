from django.contrib import admin
from landing.models import Register


class RegisterAdmin(admin.ModelAdmin):
    list_display = ['name','phone','quantity', 'bank', 'account', 'created_at']
    search_fields = ('name', 'phone', 'bank', 'account')
    ordering = ('-created_at',)


admin.site.register(Register, RegisterAdmin)