from django.contrib import admin
from .models import Brand, Product, Trade, ProdThumbnail, Like, Category, Tag, Follow, GenderDivision, FirstCategory, \
    SecondCategory, Size


# Register your models here.


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name','pk','seller','sold', 'is_refundable', 'on_discount' ,'discount_rate']
    list_editable = ('sold', 'is_refundable', 'discount_rate', 'on_discount')
    fields = ('seller', 'name', 'price', 'brand', 'first_category', 'second_category', 'size', 'content',
              'tag')


class TradeAdmin(admin.ModelAdmin):
    list_display = ['pk','product','seller','buyer', 'status']


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


admin.site.register(Brand)
admin.site.register(Product, ProductAdmin)
admin.site.register(Trade, TradeAdmin)
admin.site.register(ProdThumbnail)
admin.site.register(Like)
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Follow, FollowAdmin)

admin.site.register(GenderDivision, GenderAdmin)
admin.site.register(FirstCategory, FirstCategoryAdmin)
admin.site.register(SecondCategory, SecondCategoryAdmin)
admin.site.register(Size, SizeAdmin)

