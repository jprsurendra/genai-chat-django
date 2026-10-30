import os
from django.db import models
from django.contrib.auth.models import User


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================
def user_directory_path(instance, filename):
    """
    File will be uploaded to MEDIA_ROOT/documents/user_<id>/<filename>
    """
    # instance.user.id is used to create a separate folder for each user
    return f'documents/user_{instance.user.id}/{filename}'


# =====================================================================
# MODELS
# =====================================================================
class ChatSession(models.Model):
    """
    Represents a single conversation thread for a user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Soft delete flag: if True, the session is hidden from the UI but kept in the database
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ChatMessage(models.Model):
    """
    Represents a single message (user or AI) within a chat session.
    """
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # Soft delete flag: if True, the message is hidden from the UI but kept in the database
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class UploadedDocument(models.Model):
    """
    Represents a document uploaded by the user for RAG.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="documents", null=True,
                                     blank=True)
    # Use the custom function for upload path
    file = models.FileField(upload_to=user_directory_path)

    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    chunk_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.filename} ({self.user.username})"