from django.shortcuts import get_object_or_404
from rest_framework import serializers

from api.validation import validate_object_existence


class ToRepresentationMixin(serializers.ModelSerializer):
    read_serializer = None

    def to_representation(self, instance):
        read_serializer = self.read_serializer(instance, context=self.context)
        return read_serializer.data


class SerializerFavoriteShoppingCartMixin(serializers.ModelSerializer):
    model = None

    def get_context_data(self):
        request = self.context.get('request')
        recipe = self.context.get('view').get_object()
        return request, recipe

    def validate(self, attrs):
        request, recipe = self.get_context_data()
        validate_object_existence(
            self.model, request.user, recipe, request.method,
            exists_message='Рецепт уже добавлен',
            not_exists_message='Рецепт уже удален'
        )
        return attrs

    def create(self, validated_data):
        request, recipe = self.get_context_data()
        self.model.objects.get_or_create(user=request.user, recipe=recipe)
        return recipe

    def delete(self):
        request, recipe = self.get_context_data()
        obj = get_object_or_404(self.model, user=request.user, recipe=recipe)
        obj.delete()
        return recipe
