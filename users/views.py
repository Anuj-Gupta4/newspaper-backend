from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    ProfileResponseSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class RegisterView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(
        request=RegisterSerializer,
        responses={status.HTTP_201_CREATED: AuthResponseSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)

        return Response(
            {
                'message': 'User registered successfully.',
                'data': {
                    **tokens,
                    'user': UserProfileSerializer(user).data,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={
            status.HTTP_200_OK: AuthResponseSerializer,
            status.HTTP_401_UNAUTHORIZED: None,
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'message': 'Invalid username or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)

        return Response(
            {
                'message': 'Login successful.',
                'data': {
                    **tokens,
                    'user': UserProfileSerializer(user).data,
                },
            }
        )


class ProfileView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(responses={status.HTTP_200_OK: ProfileResponseSerializer})
    def get(self, request):
        return Response(
            {
                'message': 'User profile fetched successfully.',
                'data': UserProfileSerializer(request.user).data,
            }
        )


class RefreshTokenView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={status.HTTP_200_OK: None, status.HTTP_401_UNAUTHORIZED: None},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                'message': 'Access token refreshed successfully.',
                'data': serializer.validated_data,
            }
        )
