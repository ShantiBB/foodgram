import pytest
from django.urls import reverse
from rest_framework import status

from tests.conftest import MESSAGE


@pytest.mark.django_db
def test_tags_list(api_client_anon, get_ingredients_tags_data):
    url = reverse('tag-list')
    response = api_client_anon.get(url, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data == get_ingredients_tags_data.get('tags'), MESSAGE


@pytest.mark.django_db
def test_tag_detail(api_client_anon, tag, get_ingredients_tags_data):
    url = reverse('tag-detail', args=[tag.id])
    response = api_client_anon.get(url, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data == get_ingredients_tags_data.get('tags')[0], MESSAGE


@pytest.mark.django_db
def test_valid_field_tag(user_auth, valid_recipe_data):
    url = reverse('recipe-list')
    valid_recipe_data.pop('tags')
    response = user_auth.post(url, valid_recipe_data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    valid_recipe_data['tags'] = []
    response = user_auth.post(url, valid_recipe_data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_tag_filters(api_client_anon, create_recipe, recipe_for_filters, tag):
    filter_url = f'?tags={tag.slug}'
    urls = (reverse('recipe-list'), reverse('recipe-list') + filter_url)
    results_count = 2
    for url in urls:
        response = api_client_anon.get(url, format='json')
        results = response.data.get('results')
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == results_count
        if results_count == 1:
            tag_name = results[0].get('tags')[0].get('name')
            assert tag_name == tag.name
        results_count -= 1
