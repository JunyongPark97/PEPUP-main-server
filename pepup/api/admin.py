from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Brand, Product, Trade, ProdThumbnail, Like, Tag, Follow, GenderDivision, FirstCategory, \
    SecondCategory, Size, Payment, Deal, ProdImage, Delivery, Review


# Register your models here.


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name','pk','seller','sold', 'is_refundable', 'price', 'on_discount', 'discount_rate','discounted_price']
    list_editable = ('sold', 'is_refundable', 'discount_rate', 'on_discount')
    fields = ('seller', 'name', 'price', 'brand', 'first_category', 'second_category', 'size', 'content',
              'tag')


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


class FollowAdmin(admin.ModelAdmin):
    list_display = ['_from', '_to', 'tag', 'is_follow']


class GenderAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']


class FirstCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'is_active']


class SecondCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active']


class SizeAdmin(admin.ModelAdmin):
    list_display = ['category', 'size_name', 'get_size']

    def get_size(self, obj):
        if obj.size_max:
            return "[{}] {}-{}".format(obj.category.name, obj.size, obj.size_max)
        if obj.category.name == 'SHOES':
            return "[{}] {} (cm)".format(obj.category.name, obj.size)
        return "[{}] {}".format(obj.category.name, obj.size)


class ProdThumbnailAdmin(admin.ModelAdmin):
    list_display = ['product', 'product_id', 'thumbnails', 'pk']

    def thumbnails(self, obj):
        if obj.thumbnail:
            return mark_safe('<img src="%s" width=120px "/>' % obj.thumbnail.url)


class ProdImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'product_id', 'images', 'pk']

    def images(self, obj):
        if obj.image:
            return mark_safe('<img src="%s" width=120px "/>' % obj.image.url)


class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['sender','receiver','state','pk']


admin.site.register(Brand)
admin.site.register(Product, ProductAdmin)
admin.site.register(Trade, TradeAdmin)
admin.site.register(ProdThumbnail, ProdThumbnailAdmin)
admin.site.register(ProdImage, ProdImageAdmin)
admin.site.register(Like)
admin.site.register(Tag)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Payment,PaymentAdmin)
admin.site.register(Deal, DealAdmin)
admin.site.register(Delivery,DeliveryAdmin)


admin.site.register(GenderDivision, GenderAdmin)
admin.site.register(FirstCategory, FirstCategoryAdmin)
admin.site.register(SecondCategory, SecondCategoryAdmin)
admin.site.register(Size, SizeAdmin)

admin.site.register(Review)

