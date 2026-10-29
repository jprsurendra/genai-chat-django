from django.urls import path
from .views import ChatScreenView, LoginScreenView

urlpatterns = [
    path("", ChatScreenView.as_view(), name="index"),
    path("login/", LoginScreenView.as_view(), name="login"),
]