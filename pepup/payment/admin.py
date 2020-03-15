from django.contrib import admin
from payment.models import Commission, WalletLog, Trade, Deal, Payment, Review, DeliveryMemo
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe


class CommissionAdmin(admin.ModelAdmin):
    list_display = ['pk','rate','created_at','updated_at']
    list_editable = ('rate',)


class TradeAdmin(admin.ModelAdmin):
    list_display = ['pk', 'buyer', 'product', 'seller',  'payment', 'deal', 'status', 'created_at', 'updated_at']
    list_filter = ('status',)

    def payment(self, obj):
        if obj.deal:
            if obj.deal.payment:
                return mark_safe('<a href={}>{}</a>'.format(
                    reverse("admin:payment_payment_change", args=(obj.deal.payment.pk,)),
                    obj.deal.payment
                ))
        return '-'


class DealAdmin(admin.ModelAdmin):
    list_display = ['pk', 'buyer', 'seller', 'delivery_link', 'payment_link', 'total', 'remain', 'delivery_charge']

    def delivery_link(self, obj):
        return mark_safe('<a href={}>{}</a>'.format(
            reverse("admin:payment_delivery_change", args=(obj.delivery.pk,)),
            obj.delivery.get_state_display()
        ))

    def payment_link(self, obj):
        if obj.payment:
            return mark_safe('<a href={}>{}</a>'.format(
                reverse("admin:payment_payment_change", args=(obj.payment.pk,)),
                obj.payment
            ))
        return '-'


class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id','name','user', 'receipt_id', 'status','price','requested_at','purchased_at', 'revoked_at']
    list_filter = ('status','requested_at')


class DeliveryMemoAdmin(admin.ModelAdmin):
    list_display = ['id', 'memo', 'is_active', 'order']
    list_editable = ['order']


admin.site.register(Commission, CommissionAdmin)
admin.site.register(Trade, TradeAdmin)
admin.site.register(Deal, DealAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(WalletLog)
admin.site.register(Review)
admin.site.register(DeliveryMemo, DeliveryMemoAdmin)

