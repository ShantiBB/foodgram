from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator
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
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag, related_name='recipes', through='RecipeTag'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recipes'
    )
    ingredients = models.ManyToManyField(
        Ingredient, related_name='recipes', through='RecipeIngredient'
    )
    is_favorited = models.ManyToManyField(
        User, related_name='favorites', through='RecipeFavorite'
    )
    is_in_shopping_cart = models.ManyToManyField(
        User, related_name='shopping', through='RecipeShoppingCart'
    )
    name = models.CharField(max_length=256, unique=True)
    image = models.ImageField(upload_to='img/recipes/', null=True, blank=True)
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах'
    )
    short_link = models.CharField(
        max_length=10, unique=True, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'author'), name='unique_recipe_author'),
        )
        ordering=['-created_at']

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


class RecipeTag(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_tags'
    )
    tag = models.ForeignKey(
        Tag, on_delete=models.CASCADE,
        related_name='recipe_tags'
    )

    class Meta:
        constraints = (models.UniqueConstraint(
            fields=('recipe', 'tag'), name='unique_recipe_tag'),
        )


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        related_name='recipe_ingredients'
    )
    amount = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = (models.UniqueConstraint(
            fields=('recipe', 'ingredient'), name='unique_recipe_ingredient'),
        )
        ordering = ['ingredient__name']


class RecipeFavorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites_recipes'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='favorites_users'
    )


class RecipeShoppingCart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping_recipes'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='shopping_users'
    )
