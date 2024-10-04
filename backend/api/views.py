from django.db import models
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework import generics, mixins, status, viewsets, filters
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from .permissions import IsAuthorOrReadOnly, IsNotAuthenticatedOrReadOnly
from .serializers import (PasswordChangeSerializer, RecipeSerializer,
                          UserAvatarSerializer, UserCreateSerializer,
                          UserDetailSerializer, TagSerializer,
                          IngredientSerializer, RecipeFavoriteSerializer,
                          UserFollowSerializer)
from recipe.models import Recipe, Tag, Ingredient, Favorite
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

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=UserFollowSerializer
    )
    def subscribe(self, request, pk=None):
        following = get_object_or_404(User, pk=pk)
        follower, created = Follow.objects.get_or_create(
            following=following, follower=request.user
        )
        if request.method == 'DELETE':
            follower.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(following)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED
        )


class PasswordChangeView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer
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
            status=status.HTTP_200_OK
        )


class AvatarUpdateDeleteView(
    mixins.UpdateModelMixin,
    generics.GenericAPIView
):
    queryset = User.objects.all()
    serializer_class = UserAvatarSerializer

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
    permission_classes = [IsAuthorOrReadOnly]
    http_method_names = ('get', 'post', 'patch', 'delete')

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.all()
        if user.is_authenticated:
            favorites = Favorite.objects.filter(
                user=user, recipe=models.OuterRef('pk')
            )
            return queryset.annotate(
                _is_favorited=models.Exists(favorites)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk):
        recipe = self.get_object()
        base_url = request.build_absolute_uri('/api/s/')
        return Response(
            {'short_link': base_url + recipe.short_link},
            status=status.HTTP_200_OK
        )

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=RecipeFavoriteSerializer
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if request.method == 'DELETE':
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(recipe)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
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
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    http_method_names = ('get',)
