from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Sum
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet

from .filters import IngredientFilter, RecipeFilter
from .permissions import (IsAdminOrAuthorOrReadOnly, IsAdminOrReadOnly,
                          IsAdminOrAnonimOrReadOnly)
from .serializers import (IngredientSerializer, RecipeSerializer,
                          RecipeShortSerializer, TagSerializer,
                          UserAvatarSerializer, UserFollowSerializer)
from recipe.models import (Ingredient, Recipe, RecipeFavorite,
                           RecipeIngredient, RecipeShoppingCart, Tag)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    permission_classes = [IsAdminOrAnonimOrReadOnly]

    def partial_update(self, request, *args, **kwargs):
        """Позволяет администратору менять пароль пользователя."""
        user = self.get_object()
        if 'password' in request.data:
            password = request.data['password']
            user.set_password(password)
            user.save()
            return Response(status=status.HTTP_200_OK)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Позволяет администратору удалять пользователя."""
        user = self.get_object()
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=['PUT', 'DELETE'],
        url_path='me/avatar', permission_classes=[IsAuthenticated],
        serializer_class=UserAvatarSerializer,
    )

    def avatar(self, request):
        user = request.user
        avatar = user.avatar
        serializer = self.get_serializer(user, data=request.data)
        if request.method == 'PUT':
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if avatar:
            serializer = self.get_serializer(user)
            serializer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)


class FollowListView(generics.ListAPIView):
    serializer_class = UserFollowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return User.follows.get_follower(user).get_recipes(Recipe)


class FollowView(
    generics.GenericAPIView,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin
):
    serializer_class = UserFollowSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.follows.get_recipes(Recipe)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['recipes_count'] = self.get_object().recipes_count
        context['follower'] = self.request.user
        context['following'] = get_object_or_404(User, id=self.kwargs['pk'])
        return context

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = [IsAdminOrAuthorOrReadOnly]
    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    @staticmethod
    def get_model(model, user):
        return model.objects.filter(user=user, recipe=OuterRef('pk'))

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.all().select_related(
            'author').prefetch_related(
            'tags',
            'recipe_ingredients__ingredient',
        )
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited_for_user=Exists(
                    self.get_model(RecipeFavorite, user)
                ),
                is_in_shopping_cart_for_user=Exists(
                    self.get_model(RecipeShoppingCart, user)
                )
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def handle_models(self, model, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        context = {
            'request': request, 'model': model,
            'recipe': recipe, 'user': request.user
        }
        serializer = self.get_serializer(data=request.data, context=context)
        if request.method == 'POST':
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        serializer.is_valid(raise_exception=True)
        serializer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeShortSerializer
    )
    def favorite(self, request, pk=None):
        return self.handle_models(RecipeFavorite, request, pk)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeShortSerializer
    )
    def shopping_cart(self, request, pk=None):
        return self.handle_models(RecipeShoppingCart, request, pk)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk):
        recipe = self.get_object()
        base_url = request.build_absolute_uri('/s/')
        return Response(
            {'short-link': base_url + recipe.short_link},
            status=status.HTTP_200_OK
        )


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
    http_method_names = ('get', 'post', 'patch', 'delete')


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    http_method_names = ('get', 'post', 'patch', 'delete')


class ShoppingCartDownload(APIView):
    @staticmethod
    def get(request):
        recipes_in_cart = RecipeShoppingCart.objects.filter(
            user=request.user
        ).values_list('recipe_id', flat=True)
        ingredient_amounts = RecipeIngredient.objects.filter(
            recipe_id__in=recipes_in_cart
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        )
        lines = ['Список покупок:\n']
        for ingredient in ingredient_amounts:
            name = ingredient['ingredient__name']
            measurement_unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['total_amount']
            line = f'• {name} — {amount} {measurement_unit}'
            lines.append(line)
        content = '\n'.join(lines)
        RecipeShoppingCart.objects.filter(user=request.user).delete()
        return HttpResponse(content, content_type='text/plain')
