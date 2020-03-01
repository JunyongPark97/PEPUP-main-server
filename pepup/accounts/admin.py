from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

from .models import User, PhoneConfirm, Profile, DeliveryPolicy,Address


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name','phone','nickname')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'pk', 'nickname', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'nickname')
    ordering = ('email',)


class DeliveryPolicyAdmin(admin.ModelAdmin):
    list_display = ['seller','general','mountain','amount','volume']


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_id']

admin.site.register(PhoneConfirm)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(DeliveryPolicy,DeliveryPolicyAdmin)
admin.site.register(Address)