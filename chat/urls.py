from django.urls import path
from chat.views import (
    ChatAPIView,
    ChatStreamAPIView,
    LLMHealthView,
    UploadDocumentAPIView,
    ChatHistoryAPIView  # Import it here
)

urlpatterns = [
    # Utility Endpoints
    path("health", LLMHealthView.as_view(), name="health"),

    # API Endpoints
    path("chat", ChatAPIView.as_view(), name="chat"),
    path("chat/stream", ChatStreamAPIView.as_view(), name="chat-stream"),
    path("chat/history", ChatHistoryAPIView.as_view(), name="chat-history"), # New URL
    path("upload", UploadDocumentAPIView.as_view(), name="upload"),
]