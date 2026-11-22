from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from chat.utilities.ratelimit import check_rate_limit, get_client_ip


def _auth_rate_limited(request, scope: str):
    """
    Per-IP rate limit for unauthenticated endpoints (R11).
    Returns a 429 Response if the limit is exceeded, otherwise None.
    """
    try:
        check_rate_limit(get_client_ip(request), scope=scope, limit=settings.AUTH_RATE_LIMIT)
    except PermissionDenied as e:
        return Response({"error": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    return None


class RegisterView(APIView):
    """
    API to register a new user.
    """

    authentication_classes = ()
    permission_classes = [AllowAny]

    def post(self, request):
        limited = _auth_rate_limited(request, "register")
        if limited:
            return limited

        username = (request.data.get("username") or "").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        confirm_password = request.data.get("confirm_password") or ""

        # 1. Validation
        if not username or not email or not password or not confirm_password:
            return Response(
                {"error": "Username, email, password, and confirm password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(username) > 150:
            return Response({"error": "Username is too long."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "Enter a valid email address."}, status=status.HTTP_400_BAD_REQUEST)

        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=email).exists():
            return Response({"error": "Email already registered."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Password strength (M5): uses AUTH_PASSWORD_VALIDATORS from settings
        try:
            validate_password(password, user=User(username=username, email=email))
        except ValidationError as e:
            return Response({"error": " ".join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Create User
        User.objects.create_user(username=username, email=email, password=password)

        return Response({"message": "User created successfully."}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    API to login and receive JWT tokens.
    """

    authentication_classes = ()
    permission_classes = [AllowAny]

    def post(self, request):
        limited = _auth_rate_limited(request, "login")
        if limited:
            return limited

        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token), "username": user.username})


class RateLimitedTokenRefreshView(TokenRefreshView):
    """
    Exchanges a refresh token for a new access token (R3).
    With ROTATE_REFRESH_TOKENS=True the response also contains a new refresh token,
    and the old one is blacklisted.
    """

    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        limited = _auth_rate_limited(request, "refresh")
        if limited:
            return limited
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """
    Blacklists the refresh token so it cannot be used again.
    The access token stays valid until it expires (at most JWT_ACCESS_MINUTES).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response({"error": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(token)
            if str(refresh.get("user_id")) != str(request.user.id):
                return Response({"error": "Token does not belong to this user"}, status=status.HTTP_403_FORBIDDEN)
            refresh.blacklist()
        except TokenError:
            # Already expired or blacklisted: the user is logged out either way
            pass
        return Response({"message": "Logged out."})
