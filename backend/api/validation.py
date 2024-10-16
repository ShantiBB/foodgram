from django.contrib.auth import get_user_model
from rest_framework import exceptions

from recipe.models import Ingredient
from user.models import Follow

User = get_user_model()


def validate_subscribe(request, following):
    if following == request.user:
        raise exceptions.ValidationError('Нельзя подписаться на себя')
    if request.method == 'POST':
        validate_already_following(request.user, following)
    elif request.method == 'DELETE':
        validate_not_following(request.user, following)


def validate_already_following(follower, following):
    if Follow.objects.filter(follower=follower, following=following).exists():
        raise exceptions.ValidationError(
            'Вы уже подписаны на данного пользователя'
        )


def validate_not_following(follower, following):
    if not Follow.objects.filter(follower=follower,
                                 following=following).exists():
        raise exceptions.ValidationError(
            'Вы уже отписались от данного пользователя'
        )


def validate_object_existence(
        model, user, recipe, method, exists_message, not_exists_message
):
    obj_exists = model.objects.filter(user=user, recipe=recipe).exists()

    if method == 'POST' and obj_exists:
        raise exceptions.ValidationError(exists_message)

    if method == 'DELETE' and not obj_exists:
        raise exceptions.ValidationError(not_exists_message)

    return obj_exists


def validate_recipes_limit(request):
    if 'recipes_limit' in request.query_params:
        try:
            return int(request.query_params['recipes_limit'])
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                'recipes_limit должен быть целым числом'
            )
    return None


def validate_ingredient_data(item_data):
    ing_id = item_data.get('ingredient', {}).get('id')
    amount = item_data.get('amount')
    if not ing_id or not amount:
        raise exceptions.ValidationError('Поле c ингредиентами не заполнено')
    if amount < 1:
        raise exceptions.ValidationError(
            'Количество ингредиента должно быть больше нуля'
        )
    try:
        Ingredient.objects.get(id=ing_id)
    except Ingredient.DoesNotExist:
        raise exceptions.NotFound('Ингредиент не найден')
    return ing_id, amount


def validate_tags_and_ingredients(request, ingredients_data, tags_data):
    if request.method == 'POST':
        if not ingredients_data or not tags_data:
            raise exceptions.ValidationError(
                'Поле c ингредиентами и тегами обязательно'
            )
