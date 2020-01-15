from django.contrib import admin
from .models import Brand, Product,Trade,ProdThumbnail,Like, Category,Tag,Follow
# Register your models here.


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name','pk','seller','sold',]


class TradeAdmin(admin.ModelAdmin):
    list_display = ['pk','product','seller','buyer', 'status']


class FollowAdmin(admin.ModelAdmin):
    list_display = ['_from', '_to', 'tag', 'is_follow']


admin.site.register(Brand)
admin.site.register(Product, ProductAdmin)
admin.site.register(Trade,TradeAdmin)
admin.site.register(ProdThumbnail)
admin.site.register(Like)
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Follow,FollowAdmin)

