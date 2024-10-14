from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_superuser


class IsAdminOrAnonimOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            if view.action == 'me':
                return request.user.is_authenticated
            return True
        elif request.method == 'POST':
            if not request.user.is_authenticated or request.user.is_superuser:
                return True
        elif request.method in ['PATCH', 'DELETE']:
            return request.user.is_superuser
        return False


class IsAdminOrAuthorOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.is_superuser
