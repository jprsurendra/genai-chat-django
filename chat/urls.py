
from django.urls import path
from chat.views import ChatAPIView, ChatStreamAPIView, LLMHealthView, ChatScreenView, UploadDocumentAPIView


urlpatterns = [
    # UI Endpoint
    path("", ChatScreenView.as_view(), name="index"),

    # Utility Endpoints
    path("health", LLMHealthView.as_view(), name="health"),

    # API Endpoints
    path("api/chat", ChatAPIView.as_view(), name="chat"),
    path("api/chat/stream", ChatStreamAPIView.as_view(), name="chat-stream"),
    path("api/upload", UploadDocumentAPIView.as_view(), name="upload"),
]