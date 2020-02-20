from django.contrib import admin
from payment.models import Commission


class CommissionAdmin(admin.ModelAdmin):
    list_display = ['pk','rate','created_at','updated_at']
    list_editable = ('rate',)


admin.site.register(Commission, CommissionAdmin)