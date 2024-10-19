from rest_framework import serializers

from recipe.models import Recipe


class ToRepresentationMixin(serializers.ModelSerializer):
    read_serializer = None

    def to_representation(self, instance):
        read_serializer = self.read_serializer(instance, context=self.context)
        return read_serializer.data


class SerializerMetaMixin:

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SerializerFavoriteShoppingCartMixin(serializers.ModelSerializer):
    model = None

    class Meta:
        model = Recipe
        fields = ('id',)

    def get_context_data(self):
        request = self.context.get('request')
        recipe = self.context.get('view').get_object()
        return request, recipe

    def create(self, validated_data):
        request, recipe = self.get_context_data()
        self.model.objects.get_or_create(user=request.user, recipe=recipe)
        return recipe

    def delete(self, instance):
        request = self.context.get('request')
        obj = self.model.objects.get(user=request.user, recipe=instance)
        obj.delete()
        return instance
