from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from .utils import generate_short_link

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        max_length=32, verbose_name='Название', unique=True
    )
    slug = models.SlugField(max_length=32, unique=True, verbose_name='Слаг')

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=128, verbose_name='Название', unique=True
    )
    measurement_unit = models.CharField(
        max_length=64, verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag, related_name='recipes', through='RecipeTag', verbose_name='Теги'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recipes',
        verbose_name='Автор'
    )
    ingredients = models.ManyToManyField(
        Ingredient, related_name='recipes', through='RecipeIngredient',
        verbose_name='Ингредиенты'
    )
    is_favorited = models.ManyToManyField(
        User, related_name='favorites', through='RecipeFavorite'
    )
    is_in_shopping_cart = models.ManyToManyField(
        User, related_name='shopping', through='RecipeShoppingCart'
    )
    name = models.CharField(
        max_length=256, unique=True, verbose_name='Название'
    )
    image = models.ImageField(
        upload_to='img/recipes/', null=True, blank=True,
        verbose_name='Изображение'
    )
    text = models.TextField(verbose_name='Описание')
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах'
    )
    short_link = models.CharField(
        max_length=10, unique=True, blank=True, null=True,
        verbose_name='Короткая ссылка'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'author'), name='unique_recipe_author'),
        )
        ordering = ['-created_at']

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
        Recipe, on_delete=models.CASCADE, related_name='recipe_tags',
        verbose_name='Рецепт'
    )
    tag = models.ForeignKey(
        Tag, on_delete=models.CASCADE, related_name='recipe_tags',
        verbose_name='Тег'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        constraints = (models.UniqueConstraint(
            fields=('recipe', 'tag'), name='unique_recipe_tag'),
        )

    def __str__(self):
        return f'{self.tag.name}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)], verbose_name='Количество'
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        constraints = (models.UniqueConstraint(
            fields=('recipe', 'ingredient'), name='unique_recipe_ingredient'),
        )
        ordering = ['ingredient__name']

    def __str__(self):
        return f'{self.ingredient.name}: {self.amount}'


class RecipeFavorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites_recipes',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='favorites_users',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.recipe.name}'


class RecipeShoppingCart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping_recipes',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='shopping_users',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        return f'{self.recipe.name}'
