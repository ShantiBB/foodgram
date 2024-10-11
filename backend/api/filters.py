from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, When
from django_filters import CharFilter, FilterSet
from django_filters import rest_framework as filters
from recipe.models import Ingredient, Recipe, Tag

User = get_user_model()


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False
    )
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def filter_by_user(self, queryset, value, field_name):
        user = self.request.user
        if user.is_authenticated:
            if value:
                return queryset.filter(**{field_name: user})
            else:
                return queryset.exclude(**{field_name: user})
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        return self.filter_by_user(queryset, value, 'is_favorited')

    def filter_is_in_shopping_cart(self, queryset, name, value):
        return self.filter_by_user(queryset, value, 'is_in_shopping_cart')


class IngredientFilter(FilterSet):
    name = CharFilter(method='filter_name')

    class Meta:
        model = Ingredient
        fields = ['name']

    @staticmethod
    def filter_name(queryset, name, value):
        queryset = queryset.annotate(
            starts_with=Case(
                When(name__istartswith=value, then=1),
                default=0,
                output_field=IntegerField(),
            )
        )
        queryset = queryset.filter(name__icontains=value)
        queryset = queryset.order_by('-starts_with', 'name')
        return queryset
