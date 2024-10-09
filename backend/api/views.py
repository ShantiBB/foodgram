from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum
from django.contrib.auth import get_user_model
from rest_framework import generics, mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .permissions import (IsAdminOrAuthorOrReadOnly,
                          IsAdminOrNotAuthenticatedOrReadOnly)
from .serializers import (PasswordChangeSerializer, RecipeSerializer,
                          UserAvatarSerializer, UserCreateSerializer,
                          UserDetailSerializer, TagSerializer,
                          IngredientSerializer, RecipeShortSerializer,
                          UserFollowSerializer)
from .filters import RecipeFilter, IngredientFilter
from recipe.models import (Recipe, Tag, Ingredient,
                           RecipeFavorite, RecipeShoppingCart)
from user.models import Follow
from .validation import (validate_email_and_password,
                         validate_user_authenticated,
                         validate_user_not_authenticated,
                         get_updated_user_data, authenticate_user_for_token,
                         validate_object_existence, validate_subscribe,
                         create_or_remove_favorite_or_shopping_cart,
                         validate_new_password)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdminOrNotAuthenticatedOrReadOnly]
    http_method_names = ('get', 'post', 'patch', 'delete')

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update':
            return UserCreateSerializer
        return UserDetailSerializer

    @action(
        detail=False, methods=['get'], permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=True, methods=['post'], permission_classes=[IsAdminUser]
    )
    def set_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get('password')
        validation_response = validate_new_password(user.password, password)
        if validation_response:
            return validation_response
        user.password = password
        user.save()
        return Response(
            {"status": "Пароль успешно обновлён"},
            status=status.HTTP_200_OK
        )


class FollowListView(generics.ListAPIView):
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
        follow = Follow.objects.all()
        validate_subscribe(request, following)
        if request.method == 'POST':
            follow.create(follower=request.user, following=following)
        elif request.method == 'DELETE':
            follow.filter(follower=request.user, following=following).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        updated_user = get_updated_user_data(following)
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
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'status': 'Аватар отсутствует'}, status=status.HTTP_404_NOT_FOUND
        )


class TokenLoginView(APIView):
    @staticmethod
    def post(request):
        email = request.data.get('email')
        password = request.data.get('password')
        validate_email_and_password(email, password)
        user = authenticate_user_for_token(email, password)
        validate_user_authenticated(request)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'auth_token': token.key}, status=status.HTTP_200_OK)


class TokenLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = [IsAdminOrAuthorOrReadOnly]
    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        validate_user_not_authenticated(request.user)
        response = super().create(request, *args, **kwargs)
        response.status_code = status.HTTP_201_CREATED
        return response

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
