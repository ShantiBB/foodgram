from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (FollowListView, FollowView, IngredientViewSet,
                    RecipeViewSet, TagViewSet, CustomUserViewSet)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='customuser')
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')

urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('users/subscriptions/', FollowListView.as_view(),
         name='subscriptions'),
    path('users/<int:pk>/subscribe/', FollowView.as_view(), name='subscribe')
] + router.urls
