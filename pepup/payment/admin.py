from payment.models import Commission, WalletLog, Trade, Deal, Payment, Review, DeliveryMemo, PaymentErrorLog
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe


class CommissionAdmin(admin.ModelAdmin):
    list_display = ['pk','rate','created_at','updated_at']
    list_editable = ('rate',)


class TradeAdmin(admin.ModelAdmin):
    list_display = ['pk', 'buyer', 'product', 'seller',  'payment', 'deal', 'status', 'settable', 'created_at', 'updated_at']
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
    list_display = ['pk', 'buyer', 'seller', 'delivery_link', 'payment_link', 'transaction_completed_date',
                    'total', 'remain', 'status', 'settable','is_settled']
    list_filter = ['status', 'is_settled']

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


class WalletLogAdmin(admin.ModelAdmin):
    list_display = ['id','user', 'user_bank_info', 'deal_link','deal_remain', 'status','created_at','updated_at', 'is_settled']
    list_filter = ['status', 'created_at']
    list_editable = ['is_settled']

    def user_bank_info(self, obj):
        store_account = obj.deal.seller.account
        bank = store_account.get_bank_display()
        account = store_account.account
        holder = store_account.account_holder
        return '[예금주: {}] {}, {}'.format(holder, bank, account)

    def deal_link(self, obj):
        if obj.deal:
            return mark_safe('<a href={}>{}</a>'.format(
                reverse("admin:payment_deal_change", args=(obj.deal.pk,)),
                obj.deal
            ))
        return '-'

    def deal_remain(self, obj):
        if obj.deal:
            return '{} 원'.format(obj.deal.remain)

    deal_remain.short_description = "남은 정산액"
    user_bank_info.short_description = "판매자 계좌정보"


class DeliveryMemoAdmin(admin.ModelAdmin):
    list_display = ['id', 'memo', 'is_active', 'order']
    list_editable = ['order']


admin.site.register(Commission, CommissionAdmin)
admin.site.register(Trade, TradeAdmin)
admin.site.register(Deal, DealAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(WalletLog, WalletLogAdmin)
admin.site.register(Review)
admin.site.register(DeliveryMemo, DeliveryMemoAdmin)
admin.site.register(PaymentErrorLog)

