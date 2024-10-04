from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from drf_extra_fields.fields import Base64ImageField

from recipe.models import (
    Recipe, Tag, Ingredient, RecipeIngredient, Favorite
)
from user.models import Follow
from .mixins import PasswordChangeMixin, PasswordMixin

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )


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
    amount = serializers.IntegerField()
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
        queryset=Tag.objects.all(), many=True
    )
    author = UserDetailSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True
    )
    image = Base64ImageField(required=True)

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
        ing_id = item_data.get('ingredient').get('id')
        amount = item_data.get('amount')
        try:
            exist_ingredient = Ingredient.objects.get(id=ing_id)
        except Ingredient.DoesNotExist:
            raise NotFound(f'Ингредиент с id {ing_id} не существует')
        ingredient = RecipeIngredient.objects.create(
            recipe=instance, ingredient=exist_ingredient, amount=amount
        )
        return ingredient

    def create(self, validated_data):
        ingredients_data, tags_data = self.pop_items(validated_data)
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            self.create_ingredient(recipe, ingredient_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data, tags_data = self.pop_items(validated_data)
        instance.tags.set(tags_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # Создаем новые записи
        new_ingredients = []
        for ingredient_data in ingredients_data:
            ingredient = self.create_ingredient(instance, ingredient_data)
            new_ingredients.append(ingredient)
        # Удаляем старые записи
        exist_ingredients = instance.recipe_ingredients.all()
        ingredients = set(exist_ingredients) - set(new_ingredients)
        for ingredient in ingredients:
            ingredient.delete()
        instance.recipe_ingredients.set(new_ingredients)

        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        tags = instance.tags.all()
        representation['tags'] = TagSerializer(tags, many=True).data
        return representation

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        user = request.user
        if request and user.is_authenticated:
            favorite = Favorite.objects.filter(user=user, recipe=obj)
            return favorite.exists()
        return False


class RecipeFavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeFollowSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserFollowSerializer(serializers.ModelSerializer):
    recipes = RecipeFollowSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'avatar'
        )

    def create(self, validated_data):
        request = self.context.get('request')
        check_subscribe = validated_data['is_subscribed']
        if request and check_subscribe:
            follower = request.user
            following_id = self.instance.id
            following = User.objects.get(id=following_id)
            if following:
                follow, created = Follow.objects.get_or_create(
                    follower=follower, following=following)
                return follow
        return super().create(validated_data)


def get_is_subscribed(self, obj):
        request = self.context.get('request')
        follower = request.user
        if request and follower.is_authenticated:
            follow = Follow.objects.filter(follower=follower, following=obj)
            return follow.exists()
        return False


