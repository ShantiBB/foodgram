from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Sum
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet

from .filters import IngredientFilter, RecipeFilter
from .permissions import (IsAdminOrAuthorOrReadOnly, IsAdminOrReadOnly,
                          IsAdminOrAnonimOrReadOnly)
from .serializers import (IngredientSerializer, RecipeReadSerializer,
                          RecipeShortSerializer, TagSerializer,
                          RecipeWriteSerializer, UserAvatarSerializer,
                          UserFollowSerializer)
from recipe.models import (Ingredient, Recipe, RecipeFavorite,
                           RecipeIngredient, RecipeShoppingCart, Tag)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    permission_classes = [IsAdminOrAnonimOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        """Позволяет администратору удалять пользователя."""
        user = self.get_object()
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=['PUT'],
        url_path='me/avatar', permission_classes=[IsAuthenticated],
        serializer_class=UserAvatarSerializer,
    )
    def avatar(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        avatar = request.user.avatar
        if avatar:
            avatar.delete()
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
        # Удаление идет через сериализатор так как удаляется не сам объект,
        # а подписка на него, плюс идет валидация
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrAuthorOrReadOnly]
    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        elif self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        return super().get_serializer_class()

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

    def create_or_update_serializer(
            self, request, instance=None, partial=False
    ):
        context = {'request': request}
        serializer = self.get_serializer(
            instance=instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save(author=self.request.user)
        read_serializer = RecipeReadSerializer(recipe, context=context)
        return read_serializer

    def create(self, request, *args, **kwargs):
        read_serializer = self.create_or_update_serializer(request)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        read_serializer = self.create_or_update_serializer(
            request, instance=instance, partial=True
        )
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    def get_recipe_context(self, model, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        context = {
            'request': request,
            'model': model,
            'recipe': recipe,
            'user': request.user
        }
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        return serializer

    def handle_post(self, model, request, pk):
        serializer = self.get_recipe_context(model, request, pk)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def handle_delete(self, model, request, pk):
        # Так же удаление идет по тому же принципу, что и выше
        serializer = self.get_recipe_context(model, request, pk)
        serializer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=['post'], permission_classes=[IsAuthenticated],
        serializer_class=RecipeShortSerializer
    )
    def favorite(self, request, pk=None):
        return self.handle_post(RecipeFavorite, request, pk)

    @favorite.mapping.delete
    def remove_favorite(self, request, pk=None):
        return self.handle_delete(RecipeFavorite, request, pk)

    @action(
        detail=True, methods=['post'], permission_classes=[IsAuthenticated],
        serializer_class=RecipeShortSerializer
    )
    def shopping_cart(self, request, pk=None):
        return self.handle_post(RecipeShoppingCart, request, pk)

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        return self.handle_delete(RecipeShoppingCart, request, pk)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk):
        recipe = self.get_object()
        base_url = request.build_absolute_uri('/s/')
        return Response(
            {'short-link': base_url + recipe.short_link},
            status=status.HTTP_200_OK
        )

    @action(
        detail=False, methods=['get'], permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
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
        return HttpResponse(content, content_type='text/plain')


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
    filter_backends = [IngredientFilter]
    http_method_names = ('get', 'post', 'patch', 'delete')
