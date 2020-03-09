from django.contrib import admin
import csv
from django.contrib import messages
from django.http import HttpResponse
from pytz import unicode

from pepup_service_manager.models import Applicant, ApplyClothes, ApplicantManager, Test


class ApplyClothesInline(admin.TabularInline):

    model = ApplyClothes


class ApplicantManagerInline(admin.TabularInline):

    model = ApplicantManager


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = ['clothes_manager', 'name', 'measure_price', 'user_revenue', 'our_revenue']

        name_list = []
        for q in queryset:
            name_list.append(q.clothes_manager.user.name)
        if len(set(name_list)) > 1:
            messages.error(request,'중복선택하셨습니다. 한 사람의 정보만 export 가능합니다.')
            return None
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        response.write(u'\ufeff'.encode('utf-8'))
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"


class ApplyClothesAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ['id', 'clothes_manager', 'kinds', 'name', 'measure_price', 'user_revenue', 'our_revenue', 'sold', 'delivery', 'deposit']
    list_display_links = ['id']
    list_editable = ('name', 'measure_price', 'sold', 'delivery', 'deposit')
    search_fields = ['name', 'clothes_manager',]
    list_filter = ['kinds', 'clothes_manager', 'sold', 'delivery', 'deposit']
    actions = ["export_as_csv"]


class ApplicantAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'apply_date', 'phone', 'address']
    list_editable = ['apply_date']
    search_fields = ['name', 'phone']

    inlines = [ApplicantManagerInline]


admin.site.register(Applicant, ApplicantAdmin)
# admin.site.register(ApplicantManager)
admin.site.register(ApplyClothes, ApplyClothesAdmin)
# admin.site.register(Commission)
# admin.site.register(Test)
