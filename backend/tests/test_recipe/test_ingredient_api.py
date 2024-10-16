import pytest
from django.urls import reverse
from rest_framework import status

from tests.conftest import MESSAGE


@pytest.mark.django_db
def test_ingredients_list(api_client_anon, get_ingredients_tags_data):
    url = reverse('ingredient-list')
    response = api_client_anon.get(url, format='json')
    assert response.status_code == status.HTTP_200_OK
    ingredients = get_ingredients_tags_data.get('ingredients')[0]
    ingredients.pop('amount')
    data = get_ingredients_tags_data.get('ingredients')
    assert response.data == data, MESSAGE


@pytest.mark.django_db
def test_ingredient_detail(
        api_client_anon, ingredient, get_ingredients_tags_data
):
    url = reverse('ingredient-detail', args=[ingredient.id])
    response = api_client_anon.get(url, format='json')
    assert response.status_code == status.HTTP_200_OK
    ingredients = get_ingredients_tags_data.get('ingredients')[0]
    ingredients.pop('amount')
    data = get_ingredients_tags_data.get('ingredients')[0]
    assert response.data == data, MESSAGE


@pytest.mark.django_db
def test_valid_field_ingredient(user_auth, ingredient, valid_recipe_data):
    url = reverse('recipe-list')
    ingredients = valid_recipe_data.pop('ingredients')
    response = user_auth.post(url, valid_recipe_data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    for item in ingredients[0]:
        valid_recipe_data['ingredients'] = [{item: ingredient.id}]
        response = user_auth.post(url, valid_recipe_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    valid_recipe_data['ingredients'] = [
        {'id': ingredient.id, 'amount': -1}
    ]
    response = user_auth.post(url, valid_recipe_data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
