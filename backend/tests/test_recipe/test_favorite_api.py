import pytest
from django.urls import reverse
from pytest_lazyfixture import lazy_fixture
from rest_framework import status

from tests.conftest import MESSAGE


def check_is_favorite(response):
    is_favorite = response.data.get('is_favorited')
    return is_favorite


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, recipe, idx, prev_status_favorite, '
    'after_status_favorite', (
        (lazy_fixture('user_auth'), status.HTTP_201_CREATED,
         lazy_fixture('create_recipe'), lazy_fixture('recipe_id'),
         False, True),
        (lazy_fixture('user_auth'), status.HTTP_400_BAD_REQUEST,
         lazy_fixture('recipe_is_favorite'), lazy_fixture('recipe_id'),
         True, True),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED,
         lazy_fixture('create_recipe'), lazy_fixture('recipe_id'), False, False),
        (lazy_fixture('user_auth'), status.HTTP_404_NOT_FOUND,
         lazy_fixture('create_recipe'), 100, False, False),
    )
)
def test_make_favorite_for_recipe(
        user, status_code, recipe, idx, prev_status_favorite,
        after_status_favorite, get_short_recipes_data
):
    url = reverse('recipe-detail', args=[idx])
    if status_code != status.HTTP_404_NOT_FOUND:
        assert check_is_favorite(user.get(url)) == prev_status_favorite
    favorite_url = reverse('recipe-favorite', args=[idx])
    favorite_response = user.post(favorite_url, format='json')
    assert favorite_response.status_code == status_code
    if status_code != status.HTTP_404_NOT_FOUND:
        assert check_is_favorite(user.get(url)) == after_status_favorite
    if status_code == status.HTTP_201_CREATED:
        assert favorite_response.data == get_short_recipes_data, MESSAGE


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, recipe, idx, prev_status_favorite, '
    'after_status_favorite', (
        (lazy_fixture('user_auth'), status.HTTP_204_NO_CONTENT,
         lazy_fixture('recipe_is_favorite'), lazy_fixture('recipe_id'),
         True, False),
        (lazy_fixture('user_auth'), status.HTTP_400_BAD_REQUEST,
         lazy_fixture('create_recipe'), lazy_fixture('recipe_id'),
         False, False),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED,
         lazy_fixture('recipe_is_favorite'), lazy_fixture('recipe_id'),
         False, False),
        (lazy_fixture('user_auth'), status.HTTP_404_NOT_FOUND,
         lazy_fixture('recipe_is_favorite'), 100, True, True),
    )
)
def test_delete_favorite_for_recipe(
        user, status_code, recipe, idx, prev_status_favorite,
        after_status_favorite
):
    url = reverse('recipe-detail', args=[idx])
    if status_code != status.HTTP_404_NOT_FOUND:
        assert check_is_favorite(user.get(url)) == prev_status_favorite
    favorite_url = reverse('recipe-favorite', args=[idx])
    favorite_response = user.delete(favorite_url, format='json')
    assert favorite_response.status_code == status_code
    if status_code != status.HTTP_404_NOT_FOUND:
        assert check_is_favorite(user.get(url)) == after_status_favorite


@pytest.mark.django_db
def test_favorite_filters(user_auth, create_recipe, recipe_is_favorite, tag):
    filter_url = '?is_favorited=true'
    print(recipe_is_favorite.is_favorited)
    urls = (reverse('recipe-list'), reverse('recipe-list') + filter_url)
    results_count = 2
    for url in urls:
        response = user_auth.get(url, format='json')
        results = response.data.get('results')
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == results_count
        if results_count == 1:
            favorite = results[0].get('is_favorited')
            assert favorite
        results_count -= 1
