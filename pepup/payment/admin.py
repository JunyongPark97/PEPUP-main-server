from django.contrib import admin
from payment.models import Commission, WalletLog, Trade, Deal, Payment
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe


class CommissionAdmin(admin.ModelAdmin):
    list_display = ['pk','rate','created_at','updated_at']
    list_editable = ('rate',)


class TradeAdmin(admin.ModelAdmin):
    list_display = ['pk', 'product', 'seller', 'buyer', 'payment', 'deal', 'status']
    list_filter = ('status',)

    def payment(self, obj):
        if hasattr(obj, 'deal'):
            if hasattr(obj.deal, 'payment'):
                return mark_safe('<a href={}>{}</a>'.format(
                    reverse("admin:api_payment_change", args=(obj.deal.payment.pk,)),
                    obj.deal.payment
                ))
        return '-'


class DealAdmin(admin.ModelAdmin):
    list_display = ['pk', 'seller', 'buyer', 'payment_link', 'total', 'remain', 'delivery_charge', 'delivery_link']

    def delivery_link(self, obj):
        return mark_safe('<a href={}>{}</a>'.format(
            reverse("admin:api_delivery_change", args=(obj.delivery.pk,)),
            obj.delivery.get_state_display()
        ))

    def payment_link(self, obj):
        return mark_safe('<a href={}>{}</a>'.format(
            reverse("admin:api_payment_change", args=(obj.payment.pk,)),
            obj.payment
        ))


class PaymentAdmin(admin.ModelAdmin):
    list_display = ['name','user', 'receipt_id', 'status','price','requested_at','purchased_at', 'revoked_at']
    list_filter = ('status','requested_at')


admin.site.register(Commission, CommissionAdmin)
admin.site.register(Trade, TradeAdmin)
admin.site.register(Deal, DealAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(WalletLog)
