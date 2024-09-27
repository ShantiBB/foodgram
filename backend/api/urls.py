from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (AvatarUpdateDeleteView, PasswordChangeView, RecipeViewSet,
                    TokenLoginView, TokenLogoutView, UserViewSet)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'recipes', RecipeViewSet, basename='recipe')

urlpatterns = [
    path('users/me/avatar/', AvatarUpdateDeleteView.as_view()),
    path('users/set_password/', PasswordChangeView.as_view()),
    path('auth/token/login/', TokenLoginView.as_view()),
    path('auth/token/logout/', TokenLogoutView.as_view())
] + router.urls
