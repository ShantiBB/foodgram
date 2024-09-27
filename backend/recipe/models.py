from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from .utils import generate_short_link

User = get_user_model()


class Recipe(models.Model):
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recipes'
    )
    name = models.CharField(max_length=256)
    image = models.ImageField(upload_to='img/recipes/', null=True, blank=True)
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах'
    )
    is_favorited = models.BooleanField(default=False)
    is_in_shopping_cart = models.BooleanField(default=False)
    short_link = models.CharField(
        max_length=10, unique=True, blank=True, null=True
    )

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
