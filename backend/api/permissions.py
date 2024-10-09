from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrNotAuthenticatedOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        elif request.method == 'POST':
            return not request.user.is_authenticated
        elif request.method in ['PATCH', 'DELETE']:
            return request.user.is_superuser
        else:
            return False


class IsAdminOrAuthorOrReadOnly(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.is_superuser
