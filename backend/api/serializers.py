import hashlib

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from drf_extra_fields.fields import Base64ImageField
from recipe.models import Recipe
from rest_framework import serializers

from .mixins import PasswordChangeMixin, PasswordMixin

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )


class UserCreateSerializer(PasswordMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data['password'])
        return super(UserCreateSerializer, self).create(validated_data)


class PasswordChangeSerializer(PasswordChangeMixin, serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate_avatar(self, value):
        user = self.instance
        if user.avatar and value:
            user.avatar.open('rb')
            existing_avatar = user.avatar.read()
            user.avatar.close()
            existing_hash = hashlib.md5(existing_avatar).hexdigest()

            new_avatar = value.read()
            new_hash = hashlib.md5(new_avatar).hexdigest()
            value.seek(0)

            if existing_hash == new_hash:
                raise serializers.ValidationError(
                    "Этот аватар уже установлен.")
        return value


class RecipeSerializer(serializers.ModelSerializer):
    author = UserDetailSerializer(read_only=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def validate(self, attrs):
        user = self.context['request'].user
        if Recipe.objects.filter(author=user, name=attrs['name']).exists():
            raise serializers.ValidationError(
                "Такой рецепт уже существует")
        return attrs
