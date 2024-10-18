from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, UserManager

from .managers import UserFollowManager


class CustomUser(AbstractUser):
    email = models.EmailField(
        max_length=254, unique=True, verbose_name='Адрес электронной почты'
    )
    username = models.CharField(
        max_length=150, unique=True, verbose_name='Никнейм'
    )
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    avatar = models.ImageField(
        upload_to='img/avatar/', null=True, blank=True, verbose_name='Аватар'
    )
    objects = UserManager()
    follows = UserFollowManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def clean(self):
        from api.validation import (validate_username_field,
                                    validate_email_field)

        validate_username_field(self.username)
        validate_email_field(self.email)
        super().clean()

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super(CustomUser, self).save(*args, **kwargs)

    def __str__(self):
        return self.username


class Follow(models.Model):
    following = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='followings',
        verbose_name='Подписка'
    )
    follower = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='followers',
        verbose_name='Подписчик'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (models.UniqueConstraint(
            fields=('following', 'follower'), name='unique_follow'
        ),)

    def __str__(self):
        return self.following.username
