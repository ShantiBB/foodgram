import pytest
from django.urls import reverse
from pytest_lazyfixture import lazy_fixture
from rest_framework import status

from user.models import Follow


def check_follow(follower_user, create_user):
    followed_user = Follow.objects.filter(
        follower=follower_user, following=create_user
    )
    return followed_user.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code', (
        (lazy_fixture('subscribed_user_auth'), status.HTTP_200_OK),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED),
    )
)
def test_subscribe_list(user, status_code, get_subscribe_data):
    url = reverse('subscriptions')
    response = user.get(url)
    assert response.status_code == status_code
    if status_code == status.HTTP_200_OK:
        assert response.data['results'] == [get_subscribe_data]


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code', (
        (lazy_fixture('unsubscribed_user_auth'), status.HTTP_201_CREATED),
        (lazy_fixture('subscribed_user_auth'), status.HTTP_400_BAD_REQUEST),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED),
        (lazy_fixture('unsubscribed_user_auth'), status.HTTP_404_NOT_FOUND),
    )
)
def test_create_subscribe(
        user, status_code, follower_user, create_user, get_subscribe_data
):
    user_id = create_user.id if status_code != 404 else 100
    if status_code == status.HTTP_400_BAD_REQUEST:
        assert check_follow(follower_user, create_user)
    else:
        assert not check_follow(follower_user, create_user)
    url = reverse('subscribe', args=[user_id])
    response = user.post(url, format='json')
    assert response.status_code == status_code
    if status_code == status.HTTP_201_CREATED:
        assert response.data == get_subscribe_data
    if status_code in (201, 400):
        assert check_follow(follower_user, create_user)
    else:
        assert not check_follow(follower_user, create_user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, status_code', (
        (lazy_fixture('subscribed_user_auth'), status.HTTP_204_NO_CONTENT),
        (lazy_fixture('unsubscribed_user_auth'), status.HTTP_400_BAD_REQUEST),
        (lazy_fixture('api_client_anon'), status.HTTP_401_UNAUTHORIZED),
        (lazy_fixture('unsubscribed_user_auth'), status.HTTP_404_NOT_FOUND),
    )
)
def test_delete_subscribe(
        user, status_code, follower_user, create_user
):
    user_id = create_user.id if status_code != 404 else 100
    if status_code == status.HTTP_204_NO_CONTENT:
        assert check_follow(follower_user, create_user)
    else:
        assert not check_follow(follower_user, create_user)
    url = reverse('subscribe', args=[user_id])
    response = user.delete(url, format='json')
    assert response.status_code == status_code
    assert not check_follow(follower_user, create_user)
