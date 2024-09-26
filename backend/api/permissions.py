from rest_framework.permissions import BasePermission

class IsNotAuthenticated(BasePermission):
    """
    Разрешает доступ только неаутентифицированным пользователям.
    """

    def has_permission(self, request, view):
        if request.user.is_authenticated:
            print('123')
            return False
        return True
