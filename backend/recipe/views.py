from django.shortcuts import get_object_or_404, redirect

from .models import Recipe


def redirect_to_recipe(request, short_link):
    recipe = get_object_or_404(Recipe, short_link=short_link)
    url = request.build_absolute_uri(f'/recipes/{recipe.id}')
    return redirect(url)
