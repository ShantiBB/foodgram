from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum
from django.contrib.auth import get_user_model
from rest_framework import generics, mixins, status, viewsets, serializers
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .permissions import IsAuthorOrReadOnly, IsNotAuthenticatedOrReadOnly
from .serializers import (PasswordChangeSerializer, RecipeSerializer,
                          UserAvatarSerializer, UserCreateSerializer,
                          UserDetailSerializer, TagSerializer,
                          IngredientSerializer, RecipeFavoriteSerializer,
                          UserFollowSerializer)
from .filters import RecipeFilter, IngredientFilter
from recipe.models import (Recipe, Tag, Ingredient,
                           RecipeFavorite, RecipeShoppingCart)
from user.models import Follow

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsNotAuthenticatedOrReadOnly]
    http_method_names = ('get', 'post')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserDetailSerializer

    @action(
        detail=False, methods=['get'], permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class FollowListView(generics.ListAPIView):
    queryset = User.objects.annotate(recipes_count=Count('recipes'))
    serializer_class = UserFollowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        follower = self.request.user
        return User.objects.filter(
            followings__follower=follower
        ).annotate(
            recipes_count=Count('recipes')
        )


class FollowView(generics.UpdateAPIView):
    serializer_class = UserFollowSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'delete']

    def handle_subscribe(self, request, following):
        exist_message = 'Вы уже подписаны на данного пользователя'
        not_exist_message = 'Вы уже отписались от данного пользователя'
        self_sub_message = 'Нельзя подписаться на себя'
        exist_following = Follow.objects.filter(
            follower=request.user, following=following
        )
        if request.method == 'POST':
            if exist_following.exists():
                raise ValidationError(exist_message)
            elif following == request.user:
                raise ValidationError(self_sub_message)
            Follow.objects.create(follower=request.user, following=following)
        elif request.method == 'DELETE':
            if not exist_following.exists():
                raise ValidationError(not_exist_message)
            exist_following.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        updated_user = User.objects.annotate(
            recipes_count=Count('recipes')
        ).get(id=following.id)
        serializer = self.get_serializer(updated_user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def post(self, request, *args, **kwargs):
        following = get_object_or_404(User, id=kwargs.get('pk'))
        return self.handle_subscribe(request, following)

    def delete(self, request, *args, **kwargs):
        following = get_object_or_404(User, id=kwargs.get('pk'))
        return self.handle_subscribe(request, following)


class PasswordChangeView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'status': 'Пароль успешно изменен'},
            status=status.HTTP_204_NO_CONTENT
        )


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
            return Response(
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            {'status': 'Аватар отсутствует'},
            status=status.HTTP_404_NOT_FOUND
        )


class TokenLoginView(APIView):
    @staticmethod
    def post(request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            raise ValidationError('Требуется только email и пароль')
        user = User.objects.get(email=email)

        if not user.check_password(password):
            return Response(
                {'error': 'Неверные учетные данные'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if request.user.is_authenticated:
            raise ValidationError('Пользователь уже авторизован')
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {'auth_token': token.key}, status=status.HTTP_200_OK
        )


class TokenLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrReadOnly]
    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.status_code = status.HTTP_201_CREATED
        return response

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk):
        recipe = self.get_object()
        base_url = request.build_absolute_uri('/s/')
        return Response(
            {'short-link': base_url + recipe.short_link},
            status=status.HTTP_200_OK
        )

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeFavoriteSerializer
    )
    def handle_favorite_shopping_cart(
            self, model, request, pk, message_exists, message_not_exists):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        obj_exists = model.objects.filter(user=user, recipe=recipe).exists()
        if request.method == 'POST':
            if obj_exists:
                raise ValidationError(message_exists)
            obj = model.objects.create(user=request.user, recipe=recipe)
        elif request.method == 'DELETE':
            if not obj_exists:
                raise ValidationError(message_not_exists)
            obj = model.objects.get(user=request.user, recipe=recipe)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeFavoriteSerializer
    )
    def favorite(self, request, pk=None):
        return self.handle_favorite_shopping_cart(
            RecipeFavorite,
            request,
            pk,
            'Рецепт уже в избранном',
            'Рецепт уже удален из избранного'
        )

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeFavoriteSerializer
    )
    def shopping_cart(self, request, pk=None):
        return self.handle_favorite_shopping_cart(
            RecipeShoppingCart,
            request,
            pk,
            'Рецепт уже в cписке покупок',
            'Рецепт отсутствует в списке покупок'
        )


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    http_method_names = ('get',)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    http_method_names = ('get',)


class ShoppingCartDownload(APIView):
    @staticmethod
    def get(request):
        recipe_shopping = RecipeShoppingCart.objects.all()
        recipes_in_cart = recipe_shopping.filter(
            user=request.user
        ).values_list('recipe', flat=True)
        ingredients = Ingredient.objects.filter(
            recipe_ingredients__recipe__in=recipes_in_cart
        ).annotate(
            amount=Sum('recipe_ingredients__amount')
        ).values('name', 'measurement_unit', 'amount')
        lines = ['Список покупок:\n']
        for ingredient in ingredients:
            name = ingredient['name']
            measurement_unit = ingredient['measurement_unit']
            amount = ingredient['amount']
            line = f'• {name} — {amount} {measurement_unit}'
            lines.append(line)
        content = '\n'.join(lines)
        recipe_shopping.delete()
        return HttpResponse(content, content_type='text/plain')
