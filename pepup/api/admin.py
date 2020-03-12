from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from payment.models import Delivery
from .models import Brand, Product, ProdThumbnail, Like, Tag, Follow, GenderDivision, FirstCategory, \
    SecondCategory, Size, ProdImage, ProdS3Image


# Register your models here.


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name','pk','seller','sold', 'is_refundable', 'price', 'on_discount', 'discount_rate','discounted_price', 'is_active']
    list_editable = ('sold', 'is_refundable', 'discount_rate', 'on_discount', 'is_active')
    fields = ('seller', 'name', 'price', 'brand', 'first_category', 'second_category', 'size', 'content',
              'tag')


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


class ProdS3ImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'product_id', 'images', 'pk']

    def images(self, obj):
        if obj.image_key:
            return mark_safe('<img src="%s" width=120px "/>' % obj.image_url)


class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['sender','receiver','state','pk']


class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'tag', 'products_id']

    def products_id(self, obj):
        ids = Product.objects.filter(tag=obj).values('id').distinct()
        return ids


admin.site.register(Brand)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProdThumbnail, ProdThumbnailAdmin)
admin.site.register(ProdImage, ProdImageAdmin)
admin.site.register(ProdS3Image, ProdS3ImageAdmin)
admin.site.register(Like)
admin.site.register(Tag, TagAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Delivery, DeliveryAdmin)


admin.site.register(GenderDivision, GenderAdmin)
admin.site.register(FirstCategory, FirstCategoryAdmin)
admin.site.register(SecondCategory, SecondCategoryAdmin)
admin.site.register(Size, SizeAdmin)


