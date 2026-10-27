from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response

class LLMHealthView(APIView):
    """
    API endpoint to check if the server is running
    and which LLM provider/model is currently active.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        model = (
            settings.OLLAMA_MODEL
            if settings.LLM_PROVIDER == "ollama"
            else settings.OPENAI_MODEL
        )
        return Response(
            {"status": "ok", "provider": settings.LLM_PROVIDER, "model": model}
        )