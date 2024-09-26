from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    UserCreateListView, CurrentUserView, PasswordChangeView,
    AvatarUpdateDeleteView, TokenLoginView, TokenLogoutView
)

urlpatterns = [
    path('users/', UserCreateListView.as_view()),
    path('users/me/', CurrentUserView.as_view()),
    path('users/me/avatar/', AvatarUpdateDeleteView.as_view()),
    path('users/set_password/', PasswordChangeView.as_view()),
    path('auth/token/login/', TokenLoginView.as_view()),
    path('auth/token/logout/', TokenLogoutView.as_view())
]