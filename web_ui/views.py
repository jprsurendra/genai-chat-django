from django.shortcuts import render
from django.views import View

class ChatScreenView(View):
    """
    Renders the main chat interface (HTML).
    """
    def get(self, request):
        # Change 'index.html' to 'chat.html'
        return render(request, "web_ui/chat.html")

class LoginScreenView(View):
    """
    Renders the Login/Register page (HTML).
    """
    def get(self, request):
        return render(request, "web_ui/login.html")