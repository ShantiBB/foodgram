import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from pytest_lazyfixture import lazy_fixture
from recipe.models import Recipe, RecipeIngredient
from rest_framework import status
from tests.conftest import MESSAGE

User = get_user_model()


@pytest.mark.django_db
def test_recipes_list(api_client_anon, create_recipe, get_recipe_data):
    url = reverse('recipe-list')
    response = api_client_anon.get(url)
    assert response.status_code == status.HTTP_200_OK
    image = 'http://testserver' + create_recipe.image.url
    get_recipe_data['author']['id'] = User.objects.first().id
    get_recipe_data['id'] = create_recipe.id
    data = [{**get_recipe_data, 'image': image}]
    assert response.data['results'] == data, MESSAGE


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, data, status_code, prev_count, next_count', (
        (lazy_fixture('user_auth'), lazy_fixture('valid_recipe_data'),
         status.HTTP_201_CREATED, 0, 1),
        (lazy_fixture('user_auth'), lazy_fixture('base_recipe_data'),
         status.HTTP_400_BAD_REQUEST, 0, 0),
        (lazy_fixture('api_client_anon'), lazy_fixture('valid_recipe_data'),
         status.HTTP_401_UNAUTHORIZED, 0, 0),
    )
)
def test_recipe_create(
    user, data, status_code, prev_count,
    next_count, get_recipe_data
):
    url = reverse('recipe-list')
    recipe = Recipe.objects.all()
    assert recipe.count() == prev_count
    response = user.post(url, data, format='json')
    assert response.status_code == status_code
    assert recipe.count() == next_count
    if status_code == status.HTTP_201_CREATED:
        image = response.data.get('image')
        get_recipe_data['author']['id'] = User.objects.first().id
        get_recipe_data['id'] = recipe.first().id
        assert response.data == {**get_recipe_data, 'image': image}, MESSAGE


@pytest.mark.django_db
def test_recipe_detail(api_client_anon, create_recipe, get_recipe_data):
    url = reverse('recipe-detail', args=[create_recipe.id])
    response = api_client_anon.get(url)
    assert response.status_code == status.HTTP_200_OK
    get_recipe_data['author']['id'] = User.objects.first().id
    get_recipe_data['id'] = create_recipe.id
    image = 'http://testserver' + create_recipe.image.url
    assert response.data == {**get_recipe_data, 'image': image}, MESSAGE


def get_recipe_ingredient(idx, amount, status_code):
    if status_code == status.HTTP_200_OK:
        recipe = Recipe.objects.get(id=idx)
        ingredient = RecipeIngredient.objects.get(recipe=recipe)
        assert ingredient.amount == amount


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, idx, amount', (
        (lazy_fixture('user_auth'), status.HTTP_200_OK,
         lazy_fixture('recipe_id'), 20),
        (lazy_fixture('user_auth'), status.HTTP_400_BAD_REQUEST,
         lazy_fixture('recipe_id'), -1),
        (lazy_fixture('user_auth'), status.HTTP_404_NOT_FOUND, 100, 10),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED,
         lazy_fixture('recipe_id'), 10),
        (lazy_fixture('not_author_user'), status.HTTP_403_FORBIDDEN,
         lazy_fixture('recipe_id'), 10),
    )
)
def test_recipe_update(
        user, status_code, valid_recipe_data, idx, amount, get_recipe_data
):
    url = reverse('recipe-detail', args=[idx])
    data = valid_recipe_data['ingredients'][0]
    get_recipe_ingredient(idx, data['amount'], status_code)
    data['amount'] = amount
    response = user.patch(url, valid_recipe_data, format='json')
    assert response.status_code == status_code
    get_recipe_ingredient(idx, amount, status_code)
    if status_code == status.HTTP_200_OK:
        get_recipe_data['author']['id'] = User.objects.first().id
        get_recipe_data['id'] = idx
        image = response.data.get('image')
        get_recipe_data['ingredients'][0]['amount'] = amount
        assert response.data == {**get_recipe_data, 'image': image}, MESSAGE


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, idx, prev_count, next_count', (
        (lazy_fixture('user_auth'), status.HTTP_204_NO_CONTENT,
         lazy_fixture('recipe_id'), 1, 0),
        (lazy_fixture('user_auth'), status.HTTP_404_NOT_FOUND, 100, 1, 1),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED,
         lazy_fixture('recipe_id'), 1, 1),
        (lazy_fixture('not_author_user'), status.HTTP_403_FORBIDDEN,
         lazy_fixture('recipe_id'), 1, 1),
    )
)
def test_recipe_delete(
    user, status_code, user_auth, create_recipe, idx, prev_count, next_count
):
    recipe = Recipe.objects.all()
    url = reverse('recipe-detail', args=[idx])
    assert recipe.count() == prev_count
    response = user.delete(url, format='json')
    assert response.status_code == status_code
    assert recipe.count() == next_count
