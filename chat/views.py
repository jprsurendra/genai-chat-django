import json
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views import View
from pydantic import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .schemas import ChatRequest
from .llm import generate_reply, stream_reply
from .ratelimit import check_rate_limit

def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")

def _parse_chat_request(request) -> ChatRequest:
    try:
        data = request.data if hasattr(request, "data") else json.loads(request.body or b"{}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    try:
        return ChatRequest(**data)
    except ValidationError as e:
        raise e

class IndexView(View):
    def get(self, request):
        return render(request, "chat/index.html")

class HealthView(APIView):
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

class ChatView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            check_rate_limit(_client_ip(request))
            req = _parse_chat_request(request)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValidationError as e:
            return Response({"detail": e.errors()}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reply = async_to_sync(generate_reply)(
                req.message, req.history, req.use_fast
            )
            return Response({"reply": reply})
        except Exception as e:
            return Response(
                {"detail": f"{type(e).__name__}: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class ChatStreamView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            check_rate_limit(_client_ip(request))
            req = _parse_chat_request(request)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValidationError as e:
            return Response({"detail": e.errors()}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        async def event_gen():
            try:
                async for delta in stream_reply(
                    req.message, req.history, req.use_fast
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
        resp["Connection"] = "keep-alive"
        return resp