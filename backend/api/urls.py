from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (AvatarUpdateDeleteView, PasswordChangeView,
                    RecipeViewSet, TokenLoginView, TokenLogoutView,
                    UserViewSet, TagViewSet, IngredientViewSet,
                    FollowView, FollowListView, ShoppingCartDownload)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')

urlpatterns = [
    path('recipes/download_shopping_cart/', ShoppingCartDownload.as_view(),
         name='download_shopping_cart'),
    path('users/subscriptions/', FollowListView.as_view(),
         name='subscriptions'),
    path('users/<int:pk>/subscribe/', FollowView.as_view(), name='subscribe'),
    path('users/me/avatar/', AvatarUpdateDeleteView.as_view(), name='avatar'),
    path('users/set_password/', PasswordChangeView.as_view(),
         name='set_password'),
    path('auth/token/login/', TokenLoginView.as_view(), name='login'),
    path('auth/token/logout/', TokenLogoutView.as_view(), name='logout'),
    path('s/', include('recipe.urls')),
] + router.urls


