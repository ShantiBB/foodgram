from django.contrib import admin
from django.urls import include, path

from .views import redirect_to_recipe

urlpatterns = [
    path('<str:short_link>/', redirect_to_recipe),
]
