import base64

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from pytest_lazyfixture import lazy_fixture
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


@pytest.mark.django_db
def test_users_list(api_client_anon, create_user, get_user_data):
    url = reverse('customuser-list')
    response = api_client_anon.get(url)
    assert response.status_code == status.HTTP_200_OK
    get_user_data['id'] = User.objects.first().id
    assert response.data.get('results') == [get_user_data]


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, data, status_code, prev_count, next_count', (
        (lazy_fixture('api_client_anon'), lazy_fixture('valid_user_data'),
         status.HTTP_201_CREATED, 0, 1),
        (lazy_fixture('api_client_anon'), lazy_fixture('base_user_data'),
         status.HTTP_400_BAD_REQUEST, 0, 0),
        (lazy_fixture('not_author_user'), lazy_fixture('valid_user_data'),
         status.HTTP_403_FORBIDDEN, 1, 1)
    )
)
def test_user_create(
    user, status_code, prev_count, next_count,
    data, user_data_after_reg
):
    url = reverse('customuser-list')
    assert User.objects.all().count() == prev_count
    response = user.post(url, data, format='json')
    assert response.status_code == status_code
    if status_code == status.HTTP_201_CREATED:
        user_data_after_reg['id'] = User.objects.first().id
        assert response.data == user_data_after_reg
    assert User.objects.all().count() == next_count
    if status_code == status.HTTP_201_CREATED:
        assert User.objects.filter(username=data.get('username')).exists()
    else:
        assert not User.objects.filter(username=data.get('username')).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, user_id_or_me, status_code', (
        (lazy_fixture('api_client_anon'), lazy_fixture('user_id'),
         status.HTTP_200_OK),
        (lazy_fixture('api_client_anon'), 'me', status.HTTP_401_UNAUTHORIZED),
        (lazy_fixture('user_auth'), 'me', status.HTTP_200_OK),
    )
)
def test_user_detail(user, user_id_or_me, status_code, get_user_data):
    url = reverse('customuser-detail', args=[user_id_or_me])
    response = user.get(url)
    assert response.status_code == status_code
    if status_code == status.HTTP_200_OK:
        get_user_data['id'] = User.objects.first().id
        assert response.data == get_user_data


@pytest.mark.django_db
@pytest.mark.parametrize(
    'user, data, status_code', (
        (lazy_fixture('api_client_anon'), lazy_fixture('avatar_user_data'),
         status.HTTP_401_UNAUTHORIZED),
        (lazy_fixture('user_auth'), lazy_fixture('avatar_user_data'),
         status.HTTP_200_OK),
        (lazy_fixture('user_auth'), {}, status.HTTP_400_BAD_REQUEST)
    )
)
def test_user_avatar(user, data, status_code, create_user):
    url = reverse('customuser-avatar')
    assert not create_user.avatar
    response = user.put(url, data, format='json')
    assert response.status_code == status_code
    if status_code == status.HTTP_200_OK:
        assert create_user.avatar
        avatar_path = create_user.avatar.path
        with open(avatar_path, 'rb') as avatar_file:
            updated_image = avatar_file.read()
        avatar_base64 = data.get('avatar').split(',')[1]
        original_image = base64.b64decode(avatar_base64)
        assert updated_image == original_image
        status_codes = (status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND)
        for status_code in status_codes:
            response = user.delete(url)
            assert response.status_code == status_code
    assert not create_user.avatar


@pytest.mark.parametrize(
    'user, password_data, status_code', (
        (lazy_fixture('api_client_anon'),
         lazy_fixture('valid_set_password_data'),
         status.HTTP_401_UNAUTHORIZED),
        (lazy_fixture('user_auth'), lazy_fixture('valid_set_password_data'),
         status.HTTP_204_NO_CONTENT),
        (lazy_fixture('user_auth'), lazy_fixture('invalid_set_password_data'),
         status.HTTP_400_BAD_REQUEST),
    )
)
@pytest.mark.django_db
def test_user_set_password(user, create_user, password_data, status_code):
    url = reverse('customuser-set-password')
    if status_code == status.HTTP_204_NO_CONTENT:
        assert create_user.check_password(
            password_data.get('current_password')
        )
    response = user.post(url, password_data, format='json')
    message = f"Received status {response.status_code}: {response.data}"
    assert response.status_code == status_code, message
    if status_code == status.HTTP_204_NO_CONTENT:
        assert create_user.check_password(password_data.get('new_password'))


@pytest.mark.parametrize(
    'user, token_data, status_code', (
        (lazy_fixture('api_client_anon'), lazy_fixture('valid_token_data'),
         status.HTTP_200_OK),
        (lazy_fixture('api_client_anon'), lazy_fixture('invalid_token_data'),
         status.HTTP_400_BAD_REQUEST),
        (lazy_fixture('user_auth'), lazy_fixture('valid_token_data'),
         status.HTTP_403_FORBIDDEN),
    )
)
@pytest.mark.django_db
def test_user_token(user, create_user, token_data, status_code):
    login_url = reverse('login')
    response = user.post(login_url, token_data, format='json')
    message = f"Received status {response.status_code}: {response.data}"
    assert response.status_code == status_code, message
    if status_code == status.HTTP_200_OK:
        token_auth = Token.objects.get(user=create_user)
        assert token_auth in Token.objects.all()
        logout_url = reverse('logout')
        user.credentials(HTTP_AUTHORIZATION=f'Token {token_auth}')
        status_codes = (status.HTTP_204_NO_CONTENT,
                        status.HTTP_401_UNAUTHORIZED)
        for status_code in status_codes:
            response = user.post(logout_url)
            assert response.status_code == status_code
        assert token_auth not in Token.objects.all()
