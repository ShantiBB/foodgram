from django.urls import path

from .views import redirect_to_recipe

urlpatterns = [
    path('<str:short_link>/', redirect_to_recipe),
]
