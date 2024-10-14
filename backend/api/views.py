from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Prefetch, Sum
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
from .validation import (create_or_remove_favorite_or_shopping_cart,
                         validate_object_existence, validate_subscribe)
from user.models import Follow
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


class AvatarUpdateDeleteView(
    mixins.UpdateModelMixin,
    generics.GenericAPIView
):
    queryset = User.objects.all()
    serializer_class = UserAvatarSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        avatar = self.get_object().avatar
        if avatar:
            avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'status': 'Аватар отсутствует'}, status=status.HTTP_404_NOT_FOUND
        )


class FollowListView(generics.ListAPIView):
    serializer_class = UserFollowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        follower = self.request.user
        queryset = User.objects.filter(
            followings__follower=follower
        ).annotate(
            recipes_count=Count('recipes', distinct=True)
        ).prefetch_related(
            Prefetch(
                'recipes',
                queryset=Recipe.objects.all(),
                to_attr='prefetched_recipes'
            )
        )
        return queryset


class FollowView(generics.UpdateAPIView):
    serializer_class = UserFollowSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'delete']

    def handle_subscribe(self, request, following):
        user = request.user
        follow = Follow.objects.all()
        validate_subscribe(request, following)
        if request.method == 'POST':
            follow.create(follower=user, following=following)
        elif request.method == 'DELETE':
            follow.filter(follower=user, following=following).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        follow = Exists(follow.filter(follower=user, following=OuterRef('pk')))
        updated_user = User.objects.filter(pk=following.pk).annotate(
            recipes_count=Count('recipes', distinct=True),
            is_subscribed=follow
        ).prefetch_related(
            Prefetch(
                'recipes',
                queryset=Recipe.objects.all(),
                to_attr='prefetched_recipes'
            )
        ).first()
        serializer = self.get_serializer(updated_user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def post(self, request, *args, **kwargs):
        following = get_object_or_404(User, id=kwargs.get('pk'))
        return self.handle_subscribe(request, following)

    def delete(self, request, *args, **kwargs):
        following = get_object_or_404(User, id=kwargs.get('pk'))
        return self.handle_subscribe(request, following)


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

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeShortSerializer
    )
    def handle_favorite_shopping_cart(
            self, model, request, message_exists, message_not_exists
    ):
        recipe = self.get_object()
        user = request.user
        validate_object_existence(
            model, user, recipe, message_exists,
            message_not_exists, request.method
        )
        create_or_remove_favorite_or_shopping_cart(
            model, user, recipe, request.method
        )
        if request.method == 'DELETE':
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeShortSerializer
    )
    def favorite(self, request, pk=None):
        return self.handle_favorite_shopping_cart(
            RecipeFavorite,
            request,
            'Рецепт уже в избранном',
            'Рецепт уже удален из избранного'
        )

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeShortSerializer
    )
    def shopping_cart(self, request, pk=None):
        return self.handle_favorite_shopping_cart(
            RecipeShoppingCart,
            request,
            'Рецепт уже в cписке покупок',
            'Рецепт отсутствует в списке покупок'
        )

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
