import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.urls import reverse
from pytest_lazyfixture import lazy_fixture
from rest_framework import status

from recipe.models import Ingredient, Recipe, Tag

User = get_user_model()


def model_create(url, model, data, prev_count, next_count, user, status_code):
    assert model.objects.all().count() == prev_count
    response = user.post(url, data, format='json')
    assert response.status_code == status_code
    assert model.objects.all().count() == next_count
    if 'password' in data:
        data.pop('password')
    if status_code == status.HTTP_201_CREATED:
        assert model.objects.filter(**data).exists()
    else:
        assert not model.objects.filter(**data).exists()


def model_update(url, item, model, data, user, status_code, flag=None):
    for key, value in data.items():
        request = {key: value}
        response = user.patch(url, request, format='json')
        assert response.status_code == status_code
        if status_code == status.HTTP_200_OK:
            item.refresh_from_db()
            if key == 'password' and flag:
                assert check_password(value, item.password)
            elif key == 'password' and not flag:
                assert not check_password(value, item.password)
            else:
                assert item == model.objects.get(**request)
        else:
            assert not model.objects.filter(**request).exists()


def model_delete(url, item, model, user, status_code, prev_count, next_count):
    assert model.objects.count() == prev_count
    response = user.delete(url, format='json')
    assert response.status_code == status_code
    assert model.objects.count() == next_count
    if status_code == status.HTTP_204_NO_CONTENT:
        assert not model.objects.filter(id=item.id).exists()
    else:
        assert model.objects.filter(id=item.id).exists()


@pytest.mark.django_db
def test_create_user_only_admin(admin_auth, valid_user_data_for_admin):
    url = reverse('user-list')
    model_create(
        url, User, valid_user_data_for_admin, 1, 2,
        admin_auth, status.HTTP_201_CREATED
    )


@pytest.mark.django_db
def test_update_user_only_admin(
        admin_auth, create_user, valid_user_data_for_admin
):
    url = reverse('user-detail', args=[create_user.id])
    model_update(
        url, create_user, User, valid_user_data_for_admin,
        admin_auth, status.HTTP_200_OK, flag=True
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code', (
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED)
    )
)
def test_update_user_other(
        user, status_code, follower_user, valid_user_data_for_admin
):
    url = reverse('user-detail', args=[follower_user.id])
    model_update(
        url, follower_user, User, valid_user_data_for_admin,
        user, status_code, flag=False
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, prev_count, next_count', (
        (lazy_fixture('admin_auth'), status.HTTP_204_NO_CONTENT, 2, 1),
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN, 2, 2),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED, 1, 1)
    )
)
def test_delete_user_only_admin(
        user, status_code, prev_count, next_count, follower_user
):
    url = reverse('user-detail', args=[follower_user.id])
    model_delete(
        url, follower_user, User, user, status_code, prev_count, next_count
    )


@pytest.mark.django_db
def test_update_user_recipe_admin(
        admin_auth, create_recipe, recipe_data_for_admin
):
    url = reverse('recipe-detail', args=[create_recipe.id])
    model_update(
        url, create_recipe, Recipe, recipe_data_for_admin,
        admin_auth, status.HTTP_200_OK
    )


@pytest.mark.django_db
def test_delete_recipe_admin(
        admin_auth, create_recipe, create_user, recipe_data_for_admin
):
    url = reverse('recipe-detail', args=[create_recipe.id])
    model_delete(
        url, create_recipe, Recipe, admin_auth,
        status.HTTP_204_NO_CONTENT, 1, 0
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, prev_count, next_count', (
        (lazy_fixture('admin_auth'), status.HTTP_201_CREATED, 0, 1),
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN, 0, 0),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED, 0, 0)
    )
)
def test_create_ingredient_only_admin(
        user, status_code, prev_count, next_count, ingredient_data
):
    url = reverse('ingredient-list')
    model_create(
        url, Ingredient, ingredient_data, prev_count,
        next_count, user, status_code
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code', (
        (lazy_fixture('admin_auth'), status.HTTP_200_OK),
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED)
    )
)
def test_update_ingredient_only_admin(
        user, status_code, ingredient, ingredient_data
):
    url = reverse('ingredient-detail', args=[ingredient.id])
    model_update(
        url, ingredient, Ingredient, ingredient_data, user, status_code
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, prev_count, next_count', (
        (lazy_fixture('admin_auth'), status.HTTP_204_NO_CONTENT, 1, 0),
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN, 1, 1),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED, 1, 1)
    )
)
def test_delete_ingredient_only_admin(
        user, status_code, prev_count, next_count, ingredient
):
    url = reverse('ingredient-detail', args=[ingredient.id])
    model_delete(
        url, ingredient, Ingredient, user, status_code, prev_count, next_count
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, prev_count, next_count', (
        (lazy_fixture('admin_auth'), status.HTTP_201_CREATED, 0, 1),
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN, 0, 0),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED, 0, 0)
    )
)
def test_create_tag_only_admin(
        user, status_code, prev_count, next_count, tag_data
):
    url = reverse('tag-list')
    model_create(
        url, Tag, tag_data, prev_count, next_count, user, status_code
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code', (
        (lazy_fixture('admin_auth'), status.HTTP_200_OK),
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED)
    )
)
def test_update_tag_only_admin(
        user, status_code, tag, tag_data
):
    url = reverse('tag-detail', args=[tag.id])
    model_update(
        url, tag, Tag, tag_data, user, status_code
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code, prev_count, next_count', (
        (lazy_fixture('admin_auth'), status.HTTP_204_NO_CONTENT, 1, 0),
        (lazy_fixture('user_auth'), status.HTTP_403_FORBIDDEN, 1, 1),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED, 1, 1)
    )
)
def test_delete_tag_only_admin(
        user, status_code, prev_count, next_count, tag
):
    url = reverse('tag-detail', args=[tag.id])
    model_delete(
        url, tag, Tag, user, status_code, prev_count, next_count
    )
