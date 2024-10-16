import tempfile
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from recipe.models import Ingredient, Recipe, RecipeIngredient, Tag
from rest_framework.test import APIClient

User = get_user_model()

MESSAGE = 'Данные ответа не соответствуют ожидаемым'
PASSWORD = '12wnk1ej21'
NOT_PASSWORD = 'sdflsd123'
NEW_PASSWORD = 'm2kl31DA4'


@pytest.fixture(autouse=True)
def override_media_root(settings):
    temp_dir = tempfile.mkdtemp()
    settings.MEDIA_ROOT = temp_dir
    yield


@pytest.fixture
def api_client_anon():
    return APIClient()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_client():
    return APIClient()


@pytest.fixture
def admin_auth(admin_client):
    user = User.objects.create_superuser(
        email='admin@mail.ru', username='admin', password=PASSWORD
    )
    admin_client.force_authenticate(user=user)
    return admin_client


@pytest.fixture
def api_client_not_author():
    return APIClient()


@pytest.fixture
def create_user(api_client, valid_user_data):
    url = reverse('customuser-list')
    api_client.post(url, valid_user_data, format='json')
    user = User.objects.get(
        email=valid_user_data['email'],
        username=valid_user_data['username']
    )
    return user


@pytest.fixture
def not_author_user(api_client_not_author, django_user_model):
    user = django_user_model.objects.create(
        email='user2@test.ru',
        username='user2',
        password=PASSWORD
    )
    api_client_not_author.force_authenticate(user=user)
    return api_client_not_author


@pytest.fixture
def user_id(create_user):
    return create_user.id


@pytest.fixture
def user_auth(api_client, create_user):
    api_client.force_authenticate(user=create_user)
    return api_client


@pytest.fixture
def base_user_data():
    return {
        "email": "user@test.ru",
        "username": "user",
        "first_name": "string",
        "last_name": "string"
    }


@pytest.fixture
def valid_user_data(base_user_data):
    return {**base_user_data, "password": PASSWORD}


@pytest.fixture
def user_data_after_reg(base_user_data):
    return {**base_user_data, "id": 1}


@pytest.fixture
def get_user_data(user_data_after_reg):
    return {**user_data_after_reg, "avatar": None, "is_subscribed": False}


@pytest.fixture
def avatar_user_data():
    return {
        "avatar": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgM"
                  "AAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAO"
                  "xAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg=="
    }


@pytest.fixture
def valid_set_password_data():
    return {"current_password": PASSWORD, "new_password": NEW_PASSWORD}


@pytest.fixture
def invalid_set_password_data():
    return {"current_password": NOT_PASSWORD, "new_password": NEW_PASSWORD}


@pytest.fixture
def valid_token_data():
    return {
        "email": "user@test.ru",
        "password": PASSWORD
    }


@pytest.fixture
def invalid_token_data():
    return {
        "email": "user@test.ru",
        "password": NOT_PASSWORD
    }


@pytest.fixture
def tag(user_auth):
    return Tag.objects.create(name='tag_test', slug='slug_test')


@pytest.fixture
def tag_two(user_auth):
    return Tag.objects.create(name='tag_test_2', slug='slug_test_2')


@pytest.fixture
def ingredient(user_auth):
    return Ingredient.objects.create(name='ingredient_test',
                                     measurement_unit='unit_test')


@pytest.fixture
def ingredient_two(user_auth):
    return Ingredient.objects.create(name='ingredient_test_2',
                                     measurement_unit='unit_test_2')


@pytest.fixture
def base_recipe_data(tag, ingredient):
    load_data = {
        "name": "string",
        "text": "string",
        "cooking_time": 1
    }
    return load_data


@pytest.fixture
def valid_recipe_data(tag, ingredient, base_recipe_data):
    load_data = {
        **base_recipe_data,
        "ingredients": [{"id": ingredient.id, "amount": 10}],
        "tags": [tag.id],
        "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAA"
                 "ABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGV"
                 "Kw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg=="
    }
    return load_data


@pytest.fixture
def get_ingredients_tags_data(ingredient, tag):
    load_data = {
        "ingredients": [
            {
                "id": ingredient.id,
                "name": "ingredient_test",
                "measurement_unit": "unit_test",
                "amount": 10
            }
        ],
        "tags": [
            {
                "id": tag.id,
                "name": tag.name,
                "slug": tag.slug
            }
        ],
    }
    return load_data


@pytest.fixture
def get_recipe_data(
        get_ingredients_tags_data, get_user_data, base_recipe_data
):
    load_data = {
        **base_recipe_data,
        **get_ingredients_tags_data,
        "id": 1,
        "is_favorited": False,
        "is_in_shopping_cart": False,
        "author": get_user_data,
    }
    return load_data


@pytest.fixture
def get_short_recipes_data(create_recipe):
    return {
        "id": create_recipe.id,
        "name": create_recipe.name,
        "image": 'http://testserver' + create_recipe.image.url,
        "cooking_time": create_recipe.cooking_time
    }


@pytest.fixture
def get_subscribe_data(create_user, recipe_for_filters):
    load_data = {
        "email": create_user.email,
        "id": create_user.id,
        "username": create_user.username,
        "first_name": create_user.first_name,
        "last_name": create_user.last_name,
        "is_subscribed": True,
        "recipes": [
            {
                "id": recipe_for_filters.id,
                "name": recipe_for_filters.name,
                "image": 'http://testserver' + recipe_for_filters.image.url,
                "cooking_time": recipe_for_filters.cooking_time
            }
        ],
        "recipes_count": Recipe.objects.all().count(),
        "avatar": None,
    }
    return load_data


@pytest.fixture
def valid_user_data_for_admin():
    return {
        "email": "test_user_admin@mail.ru",
        "username": "test_user_admin",
        "first_name": "test",
        "last_name": "test",
        "password": "1223aslk312"
    }


@pytest.fixture
def get_downloaded_shopping_cart(recipe_is_in_shopping_cart):
    recipe_ingredient = RecipeIngredient.objects.get(
        recipe=recipe_is_in_shopping_cart
    )
    return f'Список покупок:\n\n' \
           f'• {recipe_ingredient.ingredient.name} — 10 unit_test'


@pytest.fixture
def create_recipe(user_auth, valid_recipe_data):
    url = reverse('recipe-list')
    user_auth.post(url, valid_recipe_data, format='json')
    recipe = Recipe.objects.get(name=valid_recipe_data['name'])
    return recipe


@pytest.fixture
def recipe_id(create_recipe):
    return create_recipe.id


@pytest.fixture
def recipe_for_filters(user_auth, valid_recipe_data, tag_two):
    url = reverse('recipe-list')
    valid_recipe_data['name'] = 'recipe_for_filters'
    valid_recipe_data['tags'] = [tag_two.id]
    user_auth.post(url, valid_recipe_data, format='json')
    recipe = Recipe.objects.get(name=valid_recipe_data['name'])
    return recipe


@pytest.fixture
def recipe_is_favorite(user_auth, recipe_for_filters):
    url = reverse('recipe-favorite', args=[recipe_for_filters.id])
    user_auth.post(url, format='json')
    return recipe_for_filters


@pytest.fixture
def recipe_is_in_shopping_cart(user_auth, recipe_for_filters):
    recipe_id = recipe_for_filters.id
    url = reverse('recipe-shopping-cart', args=[recipe_id])
    user_auth.post(url, format='json')
    return recipe_for_filters


@pytest.fixture
def subscribe_client():
    return APIClient()


@pytest.fixture
def follower_user(django_user_model):
    user = django_user_model.objects.create(
        email='user3@test.ru',
        username='user3',
        password=PASSWORD
    )
    return user


@pytest.fixture
def unsubscribed_user_auth(subscribe_client, follower_user):
    subscribe_client.force_authenticate(user=follower_user)
    return subscribe_client


@pytest.fixture
def subscribed_user_auth(subscribe_client, create_user, follower_user):
    subscribe_client.force_authenticate(user=follower_user)
    url = reverse('subscribe', args=[create_user.id])
    subscribe_client.post(url, format='json')
    return subscribe_client


@pytest.fixture
def recipe_data_for_admin(tag_two, ingredient_two):
    load_data = {
        "name": "admin_string",
        "text": "admin_string",
        "cooking_time": 10
    }
    return load_data


@pytest.fixture
def ingredient_data():
    return {
        "name": "Капуста",
        "measurement_unit": "кг"
    }


@pytest.fixture
def tag_data():
    return {
        "name": "Завтрак",
        "slug": "breakfast"
    }


@pytest.fixture
def ingredient_data_two(ingredient_two):
    return {
        "name": ingredient_two.name,
        "measurement_unit": ingredient_two.measurement_unit
    }


@pytest.fixture
def tag_data_two(tag_two):
    return {
        "name": tag_two.name,
        "slug": tag_two.slug
    }
