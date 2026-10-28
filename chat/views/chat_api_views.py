import json
from asgiref.sync import async_to_sync
from django.core.exceptions import PermissionDenied
from django.http import StreamingHttpResponse
from pydantic import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from chat.dtos import ChatRequest
from chat.utilities.llms import LLMService
from chat.utilities import check_rate_limit

from rest_framework.parsers import MultiPartParser, FormParser
import os
import tempfile

# # Create a single instance of the LLMService to be used across requests
# # This reuses the underlying AsyncOpenAI client, saving resources.
# llm_service = LLMService()


class ChatAPIView(APIView):
    """
    Base API View for handling chat requests.
    Handles common logic: Rate limiting, IP extraction, and request validation.
    """
    authentication_classes = []
    permission_classes = []

    def __init__(self, **kwargs):
        """
        Initialize the view and create an instance of LLMService.
        Lazy loading is used here to ensure Django settings are loaded before the client is created.
        """
        super().__init__(**kwargs)
        self.llm_service = LLMService()

    def generate_post_response(self, chat_request: ChatRequest):
        """
        By default, generates a Non-Streaming Response Format.
        - It waits for the complete response to arrive.
        - Once finished, it sends it all at once in JSON format.
        """
        try:
            reply = async_to_sync(self.llm_service.generate_reply)(
                chat_request.message, chat_request.history, chat_request.use_fast
            )
            return Response({"reply": reply})
        except Exception as e:
            return Response(
                {"detail": f"{type(e).__name__}: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """
        The main entry point for POST requests.
        Performs security checks and validation before generating a response.
        """
        try:
            check_rate_limit(self._client_ip(request))
            req = self._parse_chat_request(request)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValidationError as e:
            return Response({"detail": e.errors()}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ==========   Trigger the debug print for embeddings   ==========
        self.llm_service.debug_embeddings(req.message)
        # ========== ========== Test the Vector Store ========== ==========
        self.llm_service.test_manual_vector_store(req.message)
        # ===========================================

        return self.generate_post_response(req)

    def _client_ip(self, request) -> str:
        """Extracts the real client IP, considering proxies."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _parse_chat_request(self, request) -> ChatRequest:
        """Validates the incoming JSON body using Pydantic."""
        try:
            data = request.data if hasattr(request, "data") else json.loads(request.body or b"{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        try:
            return ChatRequest(**data)
        except ValidationError as e:
            raise e


class ChatStreamAPIView(ChatAPIView):
    """
    Child Class inheriting from ChatAPIView.
    Overrides ONLY the response generator to provide Streaming (SSE) instead of JSON.
    """
    authentication_classes = []
    permission_classes = []

    def generate_post_response(self, chat_request: ChatRequest):
        """
        Streaming Response Format
        - It does NOT wait for the full response.
        - As soon as the AI generates a token, it sends it immediately (SSE).
        """
        async def event_gen():
            try:
                async for delta in self.llm_service.stream_reply(
                    chat_request.message, chat_request.history, chat_request.use_fast
                ):
                    payload = json.dumps({"delta": delta})
                    yield f"data: {payload}\n\n".encode()
                yield b"data: [DONE]\n\n"
            except Exception as e:
                err = json.dumps({"error": f"{type(e).__name__}: {e}"})
                yield f"data: {err}\n\n".encode()

        resp = StreamingHttpResponse(
            event_gen(), content_type="text/event-stream"
        )
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        # Note: Remove 'Connection: keep-alive' if running on WSGI (Django's runserver)
        resp["Connection"] = "keep-alive"
        return resp


class UploadDocumentAPIView(APIView):
    """
    API endpoint to handle file uploads.
    """
    authentication_classes = []
    permission_classes = []
    parser_classes = (MultiPartParser, FormParser)  # Required for file uploads

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm_service = LLMService()

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']

        # Save the file temporarily to process it
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        try:
            # Pass to RAG engine
            result_message = self.llm_service.upload_document(temp_file_path)
            return Response({"message": result_message}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # Clean up the temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)