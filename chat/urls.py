from django.urls import path
from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("health", views.HealthView.as_view(), name="health"),
    path("api/chat", views.ChatView.as_view(), name="chat"),
    path("api/chat/stream", views.ChatStreamView.as_view(), name="chat-stream"),
]