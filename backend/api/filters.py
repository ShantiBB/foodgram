from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, When
from django_filters import FilterSet
from django_filters import rest_framework as filters
from rest_framework.filters import SearchFilter

from recipe.models import Recipe, Tag

User = get_user_model()


class RecipeFilter(FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False
    )
    is_favorited = filters.BooleanFilter(
        field_name='is_favorited_for_user',
    )
    is_in_shopping_cart = filters.BooleanFilter(
        field_name='is_in_shopping_cart_for_user',
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']


class IngredientFilter(SearchFilter):
    search_param = 'name'

    def filter_queryset(self, request, queryset, view):
        search_value = request.query_params.get(self.search_param, '')
        if search_value:
            queryset = queryset.annotate(
                starts_with=Case(
                    When(name__istartswith=search_value, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            ).filter(name__icontains=search_value)
            queryset = queryset.order_by('-starts_with', 'name')
        return queryset
