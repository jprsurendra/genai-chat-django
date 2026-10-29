from django.urls import path
from .views import RegisterView, LoginView

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),  # यह API है, जो JSON रिटर्न करेगा
]
