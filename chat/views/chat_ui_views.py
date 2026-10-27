from django.shortcuts import render
from django.views import View

class ChatScreenView(View):
    """
    Renders the main chat interface (HTML template).
    This is a standard Django View (not DRF) because it returns HTML.
    """
    def get(self, request):
        return render(request, "chat/index.html")