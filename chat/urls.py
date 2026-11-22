from django.urls import path

from chat.views import (
    ChatAPIView,
    ChatHistoryAPIView,
    ChatStreamAPIView,
    DownloadDocumentAPIView,
    LLMHealthView,
    UploadDocumentAPIView,
)

urlpatterns = [
    # Utility Endpoints
    path("health", LLMHealthView.as_view(), name="health"),
    # API Endpoints
    path("chat", ChatAPIView.as_view(), name="chat"),
    path("chat/stream", ChatStreamAPIView.as_view(), name="chat-stream"),
    path("chat/history", ChatHistoryAPIView.as_view(), name="chat-history"),
    path("upload", UploadDocumentAPIView.as_view(), name="upload"),
    # R2 FIX: the owner-checked download endpoint had no route, so the UI got 404
    path("download/<int:document_id>", DownloadDocumentAPIView.as_view(), name="download"),
]
