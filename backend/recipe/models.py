from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from .utils import generate_short_link

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(max_length=32)
    slug = models.SlugField(max_length=32, unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=128)
    measurement_unit = models.CharField(max_length=64)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    tags = models.ManyToManyField(Tag, related_name='recipes')
    ingredients = models.ManyToManyField(
        Ingredient, related_name='recipes', through='RecipeIngredient'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recipes'
    )
    name = models.CharField(max_length=256, unique=True)
    image = models.ImageField(upload_to='img/recipes/', null=True, blank=True)
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах'
    )
    is_in_shopping_cart = models.BooleanField(default=False)
    short_link = models.CharField(
        max_length=10, unique=True, blank=True, null=True
    )

    @property
    def is_favorited(self):
        return hasattr(self, '_is_favorited') and self._is_favorited

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def get_absolute_url(self):
        return reverse('recipe-detail', args=[self.id])

    def save(self, *args, **kwargs):
        if not self.short_link:
            for _ in range(10):
                short_link = generate_short_link()
                if not Recipe.objects.filter(short_link=short_link).exists():
                    self.short_link = short_link
                    break
            else:
                raise ValidationError(
                    'Не удалось сгенерировать уникальную короткую ссылку.'
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='favorites'
    )
