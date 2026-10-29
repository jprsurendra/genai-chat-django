import json
import logging
import os
import tempfile

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import StreamingHttpResponse
from asgiref.sync import async_to_sync, sync_to_async
from pydantic import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from chat.dtos import ChatRequest
from chat.utilities import check_rate_limit, get_llm_service
from chat.models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)
GENERIC_ERROR = "Something went wrong while processing your request."


class ChatAPIView(APIView):
    """
    Base View for Chat API (Non-Streaming).
    Requires a valid JWT token for access.
    """
    # JWT Authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @property
    def llm_service(self):
        return get_llm_service()

    def generate_post_response(self, chat_request: ChatRequest, user_id: str):
        try:
            reply = async_to_sync(self.llm_service.generate_reply)(
                chat_request.message, chat_request.history, str(user_id), chat_request.use_fast
            )
            return Response({"reply": reply})
        except Exception:
            logger.exception("Chat request failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            check_rate_limit(request.META.get("REMOTE_ADDR", "unknown"), scope="chat")

            # User ID is extracted from the JWT token
            user_id = request.user.id
            req = ChatRequest(**request.data)

        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValidationError as e:
            return Response({"detail": json.loads(e.json(include_url=False, include_input=False))},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # =====================================================================
        # 🎓 EDUCATIONAL NOTES: DEBUGGING & LEARNING (Commented Out for Production)
        # =====================================================================
        # Previously, we called these debug methods on every request to print
        # Embedding Similarity scores and test the manual Vector Store directly
        # in the terminal.
        #
        # Why we commented them out:
        # 1. Performance: It made 4 extra Ollama embedding calls per message, slowing down the app.
        # 2. Pollution: It seeded demo data into the real ChromaDB collection.
        #
        # If you want to test these features during development, you can uncomment
        # them or use the `python manage.py rag_demo` command.
        # ---------------------------------------------------------------------
        # self.llm_service.debug_embeddings(req.message)
        # self.llm_service.test_manual_vector_store(req.message)
        # =====================================================================

        # 1. Create or get session
        session_id = request.data.get("session_id")
        if session_id:
            session, _ = ChatSession.objects.get_or_create(id=session_id, user=request.user)
        else:
            title = req.message[:30] + "..." if len(req.message) > 30 else req.message
            session = ChatSession.objects.create(user=request.user, title=title)

        # 2. Save User Message to DB
        ChatMessage.objects.create(session=session, role="user", content=req.message)

        # 3. Get AI Response (Call LLM Non-streaming)
        response = self.generate_post_response(req, user_id)

        # 4. Save AI Reply to DB
        if response.status_code == 200:
            ai_reply = response.data.get("reply", "")
            ChatMessage.objects.create(session=session, role="assistant", content=ai_reply)

        return response

    def delete(self, request):
        try:
            check_rate_limit(request.META.get("REMOTE_ADDR", "unknown"), scope="clear")
            user_id = request.user.id
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            self.llm_service.clear_session(str(user_id))
            # Soft delete all chat history from MySQL for this user
            ChatSession.objects.filter(user=request.user).update(is_deleted=True)
            ChatMessage.objects.filter(session__user=request.user).update(is_deleted=True)
        except Exception:
            logger.exception("Clearing session failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Memory, documents, and chat history cleared."})


class ChatStreamAPIView(ChatAPIView):
    """
    Streaming View for Chat API (SSE).
    Overrides the post method to handle streaming instead of JSON.
    """

    def post(self, request):
        try:
            check_rate_limit(request.META.get("REMOTE_ADDR", "unknown"), scope="chat")
            user_id = request.user.id
            req = ChatRequest(**request.data)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValidationError as e:
            return Response({"detail": json.loads(e.json(include_url=False, include_input=False))},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Create DB Session or get existing one
        session_id = request.data.get("session_id")
        if session_id:
            session, _ = ChatSession.objects.get_or_create(id=session_id, user=request.user)
        else:
            title = req.message[:30] + "..." if len(req.message) > 30 else req.message
            session = ChatSession.objects.create(user=request.user, title=title)

        # Save User Message
        ChatMessage.objects.create(session=session, role="user", content=req.message)

        service = self.llm_service

        async def event_gen():
            full_reply = ""
            try:
                # Send the new session ID to the frontend immediately
                yield f"data: {json.dumps({'session_id': session.id})}\n\n"

                async for delta in service.stream_reply(
                        req.message, req.history, str(user_id), req.use_fast
                ):
                    full_reply += delta
                    # Note: Do NOT use .encode() here. Return a string.
                    yield f"data: {json.dumps({'delta': delta})}\n\n"

                yield "data: [DONE]\n\n"

                # Save AI reply to DB after streaming finishes
                if full_reply:
                    # Use sync_to_async to prevent SynchronousOnlyOperation error
                    await sync_to_async(ChatMessage.objects.create)(
                        session=session,
                        role="assistant",
                        content=full_reply
                    )

            except Exception as e:
                logger.error(f"Streaming exception: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': GENERIC_ERROR})}\n\n"

        resp = StreamingHttpResponse(event_gen(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp


class ChatHistoryAPIView(APIView):
    """
    API to fetch chat history for the logged-in user.
    Supports fetching all sessions, a specific session, or soft-deleting sessions.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if session_id:
            # Fetch a specific session and its messages
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user, is_deleted=False)
                # Ensure messages are fetched correctly
                messages = session.messages.filter(is_deleted=False).values('role', 'content', 'created_at')
                return Response({
                    "id": session.id,
                    "title": session.title,
                    "messages": list(messages)
                })
            except ChatSession.DoesNotExist:
                return Response({"error": "Session not found"}, status=404)

        # Fetch all active sessions for the sidebar
        sessions = ChatSession.objects.filter(user=request.user, is_deleted=False).order_by('-updated_at')
        data = [{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]
        return Response({"sessions": data})

    def delete(self, request):
        """
        Soft delete a session or all sessions.
        Pass ?session_id=123 to delete a specific session, or omit it to delete all.
        """
        session_id = request.query_params.get("session_id")

        if session_id:
            # Soft delete a specific session
            ChatSession.objects.filter(id=session_id, user=request.user).update(is_deleted=True)
            ChatMessage.objects.filter(session_id=session_id).update(is_deleted=True)
            return Response({"message": "Chat deleted successfully."})
        else:
            # Soft delete all chats for the user
            ChatSession.objects.filter(user=request.user).update(is_deleted=True)
            ChatMessage.objects.filter(session__user=request.user).update(is_deleted=True)
            return Response({"message": "All chats deleted."})

    def patch(self, request):
        """
        Rename a specific chat session.
        Expected payload: {"title": "New Chat Name"}
        Expected query param: ?session_id=123
        """
        session_id = request.query_params.get("session_id")
        new_title = request.data.get("title")

        if not session_id or not new_title:
            return Response({"error": "session_id and title are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = ChatSession.objects.get(id=session_id, user=request.user, is_deleted=False)
            session.title = new_title[:255]  # Limit title length
            session.save()
            return Response({"message": "Chat renamed successfully.", "new_title": session.title})
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)


class UploadDocumentAPIView(APIView):
    """
    View to handle PDF/TXT uploads.
    """
    # JWT Authentication Add
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    parser_classes = (MultiPartParser, FormParser)
    ALLOWED_EXT = (".pdf", ".txt")

    @property
    def llm_service(self):
        return get_llm_service()

    def post(self, request):
        try:
            upload_limit = getattr(settings, "UPLOAD_RATE_LIMIT", 5)
            check_rate_limit(request.META.get("REMOTE_ADDR", "unknown"), limit=upload_limit, scope="upload")
            user_id = request.user.id
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

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
            # Pass original filename to RAG Engine
            result_message = self.llm_service.upload_document(temp_file_path, safe_name, str(user_id))
            return Response({"message": result_message}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Upload failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if os.path.exists(temp_file_path): os.remove(temp_file_path)