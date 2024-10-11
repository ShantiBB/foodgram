from django.contrib import admin

from .models import (Ingredient, Recipe, RecipeFavorite, RecipeIngredient,
                     RecipeShoppingCart, RecipeTag, Tag)


class RecipeTagInline(admin.TabularInline):
    model = RecipeTag
    extra = 1


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


class RecipeFavoriteInline(admin.TabularInline):
    model = RecipeFavorite
    extra = 1


class RecipeShoppingCartInline(admin.TabularInline):
    model = RecipeShoppingCart
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    inlines = (
        RecipeTagInline, RecipeIngredientInline,
        RecipeFavoriteInline, RecipeShoppingCartInline
    )
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)

    readonly_fields = ('times_favorited',)
    fields = ('name', 'author', 'times_favorited')

    def times_favorited(self, obj):
        return RecipeFavorite.objects.filter(recipe=obj).count()
    times_favorited.short_description = 'Добавлений в избранное'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
