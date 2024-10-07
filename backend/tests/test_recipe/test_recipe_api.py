import pytest
from django.urls import reverse
from rest_framework import status

from recipe.models import Recipe


@pytest.mark.django_db
def test_recipes_list(client):
    url = reverse('recipe-list')
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_recipe_post(user_auth, recipe_data):
    url = reverse('recipe-list')
    assert Recipe.objects.all().count() == 0
    response = user_auth.post(url, recipe_data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert Recipe.objects.all().count() == 1