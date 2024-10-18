import pytest
from django.urls import reverse
from pytest_lazyfixture import lazy_fixture

from recipe.models import RecipeShoppingCart
from rest_framework import status
from tests.conftest import MESSAGE


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, recipe, idx, prev_status_shopping_cart, '
    'after_status_shopping_cart', (
        (lazy_fixture('user_auth'), status.HTTP_201_CREATED,
         lazy_fixture('create_recipe'), lazy_fixture('recipe_id'),
         0, 1),
        (lazy_fixture('user_auth'), status.HTTP_400_BAD_REQUEST,
         lazy_fixture('recipe_is_in_shopping_cart'), lazy_fixture('recipe_id'),
         1, 1),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED,
         lazy_fixture('recipe_is_in_shopping_cart'), lazy_fixture('recipe_id'),
         1, 1),
        (lazy_fixture('user_auth'), status.HTTP_404_NOT_FOUND,
         lazy_fixture('recipe_is_in_shopping_cart'), 100, 1, 1),
    )
)
def test_recipe_shopping_cart(
        user, status_code, recipe, idx, prev_status_shopping_cart,
        after_status_shopping_cart, get_short_recipes_data
):
    url = reverse('recipe-shopping-cart', args=[idx])
    shopping_cart = RecipeShoppingCart.objects.all()
    assert shopping_cart.count() == prev_status_shopping_cart
    response = user.post(url)
    assert response.status_code == status_code
    assert shopping_cart.count() == after_status_shopping_cart
    if status_code == status.HTTP_204_NO_CONTENT:
        assert response.data == get_short_recipes_data, MESSAGE
        response = user.delete(url)
        assert shopping_cart.count() == prev_status_shopping_cart


@pytest.mark.django_db
def test_download_shopping_cart(
        user_auth, recipe_is_in_shopping_cart, get_downloaded_shopping_cart
):
    url = reverse('recipe-download-shopping-cart')
    response = user_auth.get(url)
    content = response.content.decode('utf-8')
    assert response.status_code == status.HTTP_200_OK
    assert content == get_downloaded_shopping_cart, MESSAGE
