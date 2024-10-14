from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from .mixins import PasswordChangeMixin, PasswordMixin
from .validation import (validate_ingredient_data, validate_recipes_limit,
                         validate_tags_and_ingredients)
from user.models import Follow
from recipe.models import Ingredient, Recipe, RecipeIngredient, Tag

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


class UserFollowSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    # queryset фильтрует пользователей с подпиской, поэтому присвоил данному
    # полю True по умолчанию, чтобы не делать лишние запросы в бд
    is_subscribed = serializers.BooleanField(default=True)
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = validate_recipes_limit(request)
        recipes = getattr(obj, 'prefetched_recipes', obj.recipes.all())
        if recipes_limit is not None:
            recipes = recipes[:recipes_limit]
        serializer = RecipeShortSerializer(
            recipes, many=True, read_only=True, context=self.context
        )
        return serializer.data


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class PasswordChangeSerializer(PasswordChangeMixin):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


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
        ing_id, amount = validate_ingredient_data(item_data)
        exist_ingredient = Ingredient.objects.get(id=ing_id)
        ingredient, created = RecipeIngredient.objects.get_or_create(
            recipe=instance,
            ingredient=exist_ingredient,
            defaults={'amount': amount}
        )
        if not created:
            ingredient.amount = amount
            ingredient.save()
        return ingredient

    def set_ingredients_tags(self, validated_data, instance=None):
        request = self.context.get('request')
        ingredients_data, tags_data = self.pop_items(validated_data)
        validate_tags_and_ingredients(request, ingredients_data, tags_data)
        if request.method == 'POST':
            instance = Recipe.objects.create(**validated_data)
        else:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.recipe_ingredients.all().delete()
        if tags_data:
            instance.tags.set(tags_data)
        recipe_ingredients = []
        ingredients_id = (
            item['ingredient']['id'] for item in ingredients_data
        )
        ingredients = Ingredient.objects.filter(id__in=ingredients_id)
        ingredients_map = {
            ingredient.id: ingredient for ingredient in ingredients
        }
        for item in ingredients_data:
            ing_id, amount = validate_ingredient_data(item)
            ingredient = ingredients_map.get(ing_id)
            if ingredient:
                recipe_ingredients.append(
                    RecipeIngredient(
                        recipe=instance,
                        ingredient=ingredient,
                        amount=amount
                    )
                )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        instance.save()
        return instance

    def create(self, validated_data):
        with transaction.atomic():
            return self.set_ingredients_tags(validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            return self.set_ingredients_tags(validated_data, instance)

    @staticmethod
    def get_is_favorited(obj):
        return bool(getattr(obj, 'is_favorited_for_user', []))

    @staticmethod
    def get_is_in_shopping_cart(obj):
        return bool(getattr(obj, 'is_in_shopping_cart_for_user', []))

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        tags = instance.tags.all()
        representation['tags'] = TagSerializer(tags, many=True).data
        return representation


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
