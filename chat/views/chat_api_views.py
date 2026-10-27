import json
from asgiref.sync import async_to_sync
from django.core.exceptions import PermissionDenied
from django.http import StreamingHttpResponse
from pydantic import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from chat.dtos import ChatRequest
from chat.utilities import generate_reply, stream_reply, check_rate_limit


class ChatAPIView(APIView):
    """
    Base API View for handling chat requests.
    Handles common logic: Rate limiting, IP extraction, and request validation.
    """
    authentication_classes = []
    permission_classes = []

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

        # Calls the specific response generator (overridden by child class)
        return self.generate_post_response(req)

    def generate_post_response(self, chat_request):
        """
        By default, generates a Non-Streaming Response Format.
        - It waits for the complete response to arrive.
        - Once finished, it sends it all at once in JSON format.
        - Usage: Background tasks (e.g., generating an email).
        - Response: {"reply": "Hello, how can I help you today?"}
        """
        try:
            reply = async_to_sync(generate_reply)(
                chat_request.message, chat_request.history, chat_request.use_fast
            )
            return Response({"reply": reply})
        except Exception as e:
            return Response(
                {"detail": f"{type(e).__name__}: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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

    def generate_post_response(self, chat_request):
        """
        Streaming Response Format
        - It does NOT wait for the full response.
        - As soon as the AI generates a token, it sends it immediately (SSE).
        - Response:
                data: {"delta": "Hello"}
                data: {"delta": ", how"}
                data: [DONE]
        - Usage: Chat UI where live typing is shown to the user.
        """

        async def event_gen():
            try:
                # Iterate over the async generator from utilities/llm.py
                async for delta in stream_reply(
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

        # Note: 'Connection: keep-alive' is not allowed in WSGI (Django runserver),
        # but is handled automatically by ASGI (Uvicorn). If you get an error, remove this line.
        resp["Connection"] = "keep-alive"
        return resp