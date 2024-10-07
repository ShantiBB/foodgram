from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    )

    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=256, choices=ROLE_CHOICES, default='user'
    )
    avatar = models.ImageField(upload_to='img/avatar/', null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Follow(models.Model):
    following = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='followings'
    )
    follower = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='followers'
    )

    class Meta:
        constraints = (models.UniqueConstraint(
            fields=('following', 'follower'), name='unique_follow'
        ),)
