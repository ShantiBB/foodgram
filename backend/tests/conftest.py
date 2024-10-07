import pytest
from django.contrib.auth import get_user_model
from django.test.client import Client
from django.urls import reverse
from rest_framework.test import APIClient

from recipe.models import Tag, Ingredient, Recipe, RecipeTag, RecipeIngredient

User = get_user_model()

PASSWORD = '12wnk1ej21'
NOT_PASSWORD = 'sdflsd123'
NEW_PASSWORD = 'm2kl31DA4'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def invalid_user_data():
    return {
        "email": "user@test.ru",
        "username": "user",
        "first_name": "string",
        "last_name": "string"
    }


@pytest.fixture
def valid_user_data(invalid_user_data):
    return {**invalid_user_data, "password": PASSWORD}


@pytest.fixture
def user_data_after_reg(invalid_user_data):
    return {**invalid_user_data, "id": 1}


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
def create_user(api_client, valid_user_data):
    url = reverse('user-list')
    response = api_client.post(url, valid_user_data, format='json')
    user = User.objects.get(
        email=valid_user_data['email'],
        username=valid_user_data['username']
    )
    return user


@pytest.fixture
def user_id(create_user):
    return create_user.id


@pytest.fixture
def user_auth(api_client, create_user):
    api_client.force_authenticate(user=create_user)
    return api_client


@pytest.fixture
def tag(user_auth):
    return Tag.objects.create(name='tag_test', slug='slug_test')


@pytest.fixture
def ingredient(user_auth):
    return Ingredient.objects.create(name='ingredient_test',
                                     measurement_unit='unit_test')


@pytest.fixture
def recipe_data(tag, ingredient):
    load_data = {
        "ingredients": [
            {
                "id": ingredient.id,
                "amount": 10
            }
        ],
        "tags": [
            tag.id
        ],
        "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAA"
                 "ABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGV"
                 "Kw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
        "name": "string",
        "text": "string",
        "cooking_time": 1
    }
    return load_data
