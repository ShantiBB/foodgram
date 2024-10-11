from django.contrib import admin

from .models import CustomUser, Follow


class FollowTagInline(admin.TabularInline):
    model = Follow
    extra = 1
    fk_name = 'follower'


@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email')
    inlines = (FollowTagInline,)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (
            'Персональная информация',
            {'fields': ('first_name', 'last_name', 'email', 'avatar')}
        ),
        (
            'Права доступа',
            {'fields': ('is_active', 'is_staff', 'is_superuser')}
        ),
    )
    search_fields = ('username', 'email')
