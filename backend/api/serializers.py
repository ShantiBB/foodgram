from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound, AuthenticationFailed
from rest_framework.serializers import ValidationError
from drf_extra_fields.fields import Base64ImageField
from rest_framework.response import Response

from foodgram_backend.settings import REST_FRAMEWORK
from recipe.models import (Recipe, Tag, Ingredient, RecipeIngredient,
                           RecipeFavorite, RecipeShoppingCart)
from user.models import Follow
from .mixins import PasswordChangeMixin, PasswordMixin

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        follower = request.user
        if request and follower.is_authenticated:
            follow = Follow.objects.filter(follower=follower, following=obj)
            return follow.exists()
        return False


class UserCreateSerializer(PasswordMixin):
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        encrypt_password = make_password(validated_data['password'])
        validated_data['password'] = encrypt_password
        return super(UserCreateSerializer, self).create(validated_data)


class PasswordChangeSerializer(PasswordChangeMixin):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    amount = serializers.IntegerField(required=True)
    name = serializers.CharField(
        source='ingredient.name', read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'amount', 'measurement_unit')


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=True
    )
    author = UserDetailSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True
    )
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    @staticmethod
    def pop_items(validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', '')
        tags_data = validated_data.pop('tags', '')
        return ingredients_data, tags_data

    @staticmethod
    def create_ingredient(instance, item_data):
        if not item_data:
            raise serializers.ValidationError(
                'Поле c ингредиентами не может быть пустым'
            )
        try:
            ing_id = item_data.get('ingredient', {}).get('id')
            amount = item_data.get('amount')
            if not ing_id or not amount:
                raise serializers.ValidationError(
                    'Поле c ингредиентами не заполнено'
                )
            if amount < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть больше нуля'
                )
            exist_ingredient = Ingredient.objects.get(id=ing_id)
        except Ingredient.DoesNotExist:
            raise NotFound(f'Ингредиент не найден')
        ingredient, created = RecipeIngredient.objects.get_or_create(
            recipe=instance,
            ingredient=exist_ingredient,
            defaults={'amount': amount}
        )
        if not created:
            ingredient.amount = amount
            ingredient.save()
        return ingredient

    def create(self, validated_data):
        if self.context.get('request').user.is_anonymous:
            raise AuthenticationFailed('Пользователь не авторизован')
        with transaction.atomic():
            ingredients_data, tags_data = self.pop_items(validated_data)
            recipe = Recipe.objects.create(**validated_data)
            recipe.tags.set(tags_data)
            for ingredient_data in ingredients_data:
                self.create_ingredient(recipe, ingredient_data)
        return recipe

    def update(self, instance, validated_data):
        with transaction.atomic():
            ingredients_data, tags_data = self.pop_items(validated_data)
            instance.tags.set(tags_data)
            instance.recipe_ingredients.all().delete()
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            for ingredient_data in ingredients_data:
                self.create_ingredient(instance, ingredient_data)
            instance.save()
        return instance

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        user = request.user
        if request and user.is_authenticated:
            favorite = RecipeFavorite.objects.filter(user=user, recipe=obj)
            return favorite.exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        user = request.user
        if request and user.is_authenticated:
            shopping = RecipeShoppingCart.objects.filter(user=user, recipe=obj)
            return shopping.exists()
        return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        tags = instance.tags.all()
        representation['tags'] = TagSerializer(tags, many=True).data
        return representation


class RecipeFavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserFollowSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()
        if 'recipes_limit' in request.query_params:
            try:
                recipes_limit = int(request.query_params['recipes_limit'])
            except (TypeError, ValueError):
                raise ValidationError('recipes_limit должен быть целым числом')
            recipes = obj.recipes.all()[:recipes_limit]
        serializer = RecipeFavoriteSerializer(
            recipes, many=True, read_only=True
        )
        return serializer.data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        follower = request.user
        if request and follower.is_authenticated:
            follow = Follow.objects.filter(follower=follower, following=obj)
            return follow.exists()
        return False
