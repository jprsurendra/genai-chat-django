import json
import logging
import os
import tempfile

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import StreamingHttpResponse
from asgiref.sync import async_to_sync
from pydantic import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.dtos import ChatRequest
from chat.utilities import check_rate_limit, get_llm_service
from chat.utilities.rags.rag_engine import is_valid_session_id

logger = logging.getLogger(__name__)
GENERIC_ERROR = "Something went wrong while processing your request."


class SessionMixin:
    """Mixin to handle IP extraction and Session ID validation."""

    def _client_ip(self, request) -> str:
        if settings.TRUST_X_FORWARDED_FOR:
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            if xff: return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _session_id(self, request) -> str:
        sid = request.META.get("HTTP_X_SESSION_ID", "")
        if not is_valid_session_id(sid):
            raise ValueError("Missing or invalid X-Session-Id header.")
        return sid


class ChatAPIView(SessionMixin, APIView):
    """Base View for Chat API (Non-Streaming)."""
    authentication_classes = []
    permission_classes = []

    @property
    def llm_service(self):
        return get_llm_service()

    def generate_post_response(self, chat_request: ChatRequest, session_id: str):
        try:
            reply = async_to_sync(self.llm_service.generate_reply)(
                chat_request.message, chat_request.history, session_id, chat_request.use_fast
            )
            return Response({"reply": reply})
        except Exception:
            logger.exception("Chat request failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            check_rate_limit(self._client_ip(request), scope="chat")
            session_id = self._session_id(request)
            req = ChatRequest(**request.data)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValidationError as e:
            return Response({"detail": json.loads(e.json(include_url=False, include_input=False))},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return self.generate_post_response(req, session_id)

    def delete(self, request):
        try:
            check_rate_limit(self._client_ip(request), scope="clear")
            session_id = self._session_id(request)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.llm_service.clear_session(session_id)
        except Exception:
            logger.exception("Clearing session failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Memory and uploaded documents cleared."})


class ChatStreamAPIView(ChatAPIView):
    """Streaming View for Chat API (SSE)."""

    def generate_post_response(self, chat_request: ChatRequest, session_id: str):
        # Get the service once
        service = self.llm_service

        # Define the async generator
        async def event_gen():
            try:
                async for delta in service.stream_reply(
                        chat_request.message, chat_request.history, session_id, chat_request.use_fast
                ):
                    yield f"data: {json.dumps({'delta': delta})}\n\n".encode()
                yield b"data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming exception: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': GENERIC_ERROR})}\n\n".encode()

        # Return the StreamingHttpResponse
        resp = StreamingHttpResponse(event_gen(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"

        # Note: If you get a hop-by-hop header error, remove the 'Connection' line below.
        # resp["Connection"] = "keep-alive"

        return resp


class UploadDocumentAPIView(SessionMixin, APIView):
    """View to handle PDF/TXT uploads."""
    authentication_classes = []
    permission_classes = []
    parser_classes = (MultiPartParser, FormParser)
    ALLOWED_EXT = (".pdf", ".txt")

    @property
    def llm_service(self):
        return get_llm_service()

    def post(self, request):
        try:
            upload_limit = getattr(settings, "UPLOAD_RATE_LIMIT", 5)
            check_rate_limit(self._client_ip(request), limit=upload_limit, scope="upload")
            session_id = self._session_id(request)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if "file" not in request.FILES:
            return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES["file"]
        safe_name = os.path.basename(uploaded_file.name or "upload")
        ext = os.path.splitext(safe_name)[1].lower()

        if ext not in self.ALLOWED_EXT:
            return Response({"detail": "Unsupported format."}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded_file.size > settings.RAG_MAX_UPLOAD_BYTES:
            return Response({"detail": "File too large."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        try:
            result_message = self.llm_service.upload_document(temp_file_path, session_id)
            return Response({"message": result_message}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Upload failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if os.path.exists(temp_file_path): os.remove(temp_file_path)