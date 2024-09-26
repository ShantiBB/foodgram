from django.contrib.auth import get_user_model, authenticate
from rest_framework import status, generics, mixins
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import (
    UserCreateSerializer, UserDetailSerializer,
    PasswordChangeSerializer, UserAvatarSerializer
)
from .authentication import BearerAuthentication
from .permissions import IsNotAuthenticated

User = get_user_model()


class UserCreateListView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin
):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"detail": "Вы уже авторизованы."},
                            status=status.HTTP_403_FORBIDDEN)
        return self.create(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method.lower() == 'post':
            return UserCreateSerializer
        return super().get_serializer_class()



class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        print("request.user:", request.user)
        print("request.user.is_authenticated:", request.user.is_authenticated)
        user = request.user
        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)




class PasswordChangeView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'status': 'Пароль успешно изменен'},
            status=status.HTTP_200_OK
        )


class AvatarUpdateDeleteView(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView
):
    serializer_class = UserAvatarSerializer
    authentication_classes = [BearerAuthentication]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.avatar.delete(save=True)
        return Response(
            {'status': 'Аватар успешно удален'},
            status=status.HTTP_204_NO_CONTENT
        )


class TokenLoginView(APIView):

    @staticmethod
    def post(request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'auth_token': str(refresh.access_token),
                'refresh_token': str(refresh)
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Неверные email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class TokenLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request):
        refresh_token = request.data.get("refresh_token")
        token = RefreshToken(refresh_token)
        try:
            token.blacklist()
            return Response({"detail": "Token blacklisted successfully"},
                            status=200)
        except TokenError as e:
            return Response({"detail": str(e)}, status=400)
