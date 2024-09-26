from django.contrib import admin

from .models import CustomUser


@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (
            'Personal information',
            {'fields': ('first_name', 'last_name', 'email', 'avatar')}
        ),
        (
            'Permissions',
            {'fields': ('is_active', 'is_staff', 'is_superuser', 'role',)}
        ),
    )
