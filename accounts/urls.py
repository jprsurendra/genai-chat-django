from django.urls import path

from .views import LoginView, LogoutView, RateLimitedTokenRefreshView, RegisterView

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),  # यह API है, जो JSON रिटर्न करेगा
    path("refresh", RateLimitedTokenRefreshView.as_view(), name="token-refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
]
