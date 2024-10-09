from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to='img/avatar/', null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super(CustomUser, self).save(*args, **kwargs)

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
