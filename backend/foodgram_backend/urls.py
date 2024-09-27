from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('s/', include('recipe.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
