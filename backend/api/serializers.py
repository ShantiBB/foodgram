from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from .validation import (validate_recipes_limit, validate_ingredient_data,
                         validate_tags_and_ingredients, validate_subscribe,
                         validate_username_field, validate_email_field,
                         validate_object_existence)
from .mixins import (ToRepresentationMixin, SerializerMetaMixin,
                     SerializerFavoriteShoppingCartMixin)
from user.models import Follow
from recipe.models import (Ingredient, Recipe, RecipeIngredient, Tag,
                           RecipeFavorite, RecipeShoppingCart)

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj: User) -> bool:
        request = self.context.get('request')
        follower = request.user
        if request and follower.is_authenticated:
            follow = Follow.objects.filter(follower=follower, following=obj)
            return follow.exists()
        return False


class UserShortDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name')


class UserCreateSerializer(ToRepresentationMixin):
    read_serializer = UserShortDetailSerializer

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )

    @staticmethod
    def validate_username(value: str) -> str:
        validate_username_field(value)
        return value

    @staticmethod
    def validate_email(value: str) -> str:
        validate_email_field(value)
        return value


class UserFollowDetailSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    is_subscribed = serializers.BooleanField(default=True)
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    @staticmethod
    def get_recipes_count(obj: User) -> int:
        recipes_count = obj.recipes_count
        if recipes_count:
            return recipes_count
        return getattr(obj, 'recipes_count', 0)

    def get_recipes(self, obj: User) -> list:
        request = self.context.get('request')
        recipes_limit = validate_recipes_limit(request)
        recipes = getattr(obj, 'prefetched_recipes', obj.recipes.all())
        if recipes_limit is not None:
            recipes = recipes[:recipes_limit]
        serializer = RecipeShortDetailSerializer(
            recipes, many=True, read_only=True, context=self.context
        )
        return serializer.data


class UserFollowCreateSerializer(ToRepresentationMixin):
    read_serializer = UserFollowDetailSerializer

    class Meta:
        model = User
        fields = ('id',)

    def get_follower_and_following_user(self) -> tuple:
        request = self.context.get('request')
        view = self.context.get('view')
        follower = request.user
        following = view.get_object()
        return follower, following

    def validate(self, attrs: dict) -> dict:
        request = self.context.get('request')
        follower, following = self.get_follower_and_following_user()
        validate_subscribe(request, following)
        return attrs

    def create(self, validated_data: dict) -> User:
        follower, following = self.get_follower_and_following_user()
        Follow.objects.create(follower=follower, following=following)
        return following

    def delete(self, following) -> User:
        request = self.context.get('request')
        follower = request.user
        follow = Follow.objects.filter(follower=follower, following=following)
        follow.delete()
        return following


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(
        source='ingredient.name'
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'amount', 'measurement_unit')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author = UserDetailSerializer(read_only=True)
    ingredients = RecipeIngredientDetailSerializer(
        source='recipe_ingredients',
        many=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    @staticmethod
    def get_is_favorited(obj: Recipe) -> bool:
        return bool(getattr(obj, 'is_favorited_for_user', []))

    @staticmethod
    def get_is_in_shopping_cart(obj: Recipe) -> bool:
        return bool(getattr(obj, 'is_in_shopping_cart_for_user', []))


class RecipeShortDetailSerializer(
    SerializerMetaMixin,
    serializers.ModelSerializer
):
    pass


class RecipeCreateSerializer(ToRepresentationMixin):
    # Вынес to_representations в отдельный миксин
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=True
    )
    ingredients = RecipeIngredientCreateSerializer(
        source='recipe_ingredients',
        many=True
    )
    image = Base64ImageField()
    read_serializer = RecipeDetailSerializer

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'author',
            'image', 'name', 'text', 'cooking_time'
        )
        read_only_fields = ('author',)

    @staticmethod
    def get_ingredient_data(item_data: dict) -> tuple:
        ing_id = item_data.get('ingredient', {}).get('id')
        amount = item_data.get('amount')
        return ing_id, amount

    def validate(self, data: dict) -> dict:
        request = self.context.get('request')
        ingredients = data.get('recipe_ingredients', [])
        tags = data.get('tags', [])
        validate_tags_and_ingredients(request, ingredients, tags)
        for item in ingredients:
            ing_id, amount = self.get_ingredient_data(item)
            validate_ingredient_data(ing_id, amount)
        return data

    @staticmethod
    def pop_items(validated_data: dict) -> tuple:
        ingredients_data = validated_data.pop('recipe_ingredients', '')
        tags_data = validated_data.pop('tags', '')
        return ingredients_data, tags_data

    def set_ingredients_tags(
            self, ingredients_data: dict,
            tags_data: dict,
            instance: Recipe = None
    ) -> Recipe:
        if tags_data:
            instance.tags.set(tags_data)
        recipe_ingredients = []
        for item in ingredients_data:
            ing_id, amount = self.get_ingredient_data(item)
            recipe_ingredients.append(
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=ing_id,
                    amount=amount
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        instance.save()
        return instance

    def create(self, validated_data: dict) -> Recipe:
        with transaction.atomic():
            ingredients_data, tags_data = self.pop_items(validated_data)
            recipe = Recipe.objects.create(**validated_data)
            return self.set_ingredients_tags(
                ingredients_data, tags_data, instance=recipe
            )

    def update(self, instance: Recipe, validated_data: dict) -> Recipe:
        with transaction.atomic():
            ingredients_data, tags_data = self.pop_items(validated_data)
            super().update(instance, validated_data)
            instance.recipe_ingredients.all().delete()
            return self.set_ingredients_tags(
                ingredients_data, tags_data, instance=instance
            )


class RecipeFavoriteDetailSerializer(
    SerializerMetaMixin,
    serializers.ModelSerializer
):
    model = RecipeFavorite


class RecipeFavoriteCreateSerializer(
    SerializerFavoriteShoppingCartMixin,
    ToRepresentationMixin
):
    model = RecipeFavorite
    read_serializer = RecipeFavoriteDetailSerializer

    def validate(self, attrs):
        request, recipe = self.get_context_data()
        validate_object_existence(
            self.model, request.user, recipe, request.method,
            exists_message='Рецепт уже добавлен в избранное',
            not_exists_message='Рецепт уже удален из избранного'
        )
        return attrs


class RecipeShoppingCartDetailSerializer(
    SerializerMetaMixin,
    serializers.ModelSerializer
):
    model = RecipeShoppingCart


class RecipeShoppingCartCreateSerializer(
    SerializerFavoriteShoppingCartMixin,
    ToRepresentationMixin
):
    model = RecipeShoppingCart
    read_serializer = RecipeShoppingCartDetailSerializer

    def validate(self, attrs):
        request, recipe = self.get_context_data()
        validate_object_existence(
            self.model, request.user, recipe, request.method,
            exists_message='Рецепт уже добавлен в список покупок',
            not_exists_message='Рецепт уже удален из списка покупок'
        )
        return attrs
