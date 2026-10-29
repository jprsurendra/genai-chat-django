from django.db import models
from django.contrib.auth.models import User

class ChatSession(models.Model):
    """
    Represents a single conversation thread for a user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class UploadedDocument(models.Model):
    """
    Represents a document uploaded by the user for RAG.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    chunk_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.filename} ({self.user.username})"