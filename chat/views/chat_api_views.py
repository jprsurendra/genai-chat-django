import hashlib
import json
import logging
import os

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import StreamingHttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync, sync_to_async
from pydantic import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from chat.dtos import ChatRequest
from chat.dtos import ChatMessage as ChatMessageDTO
from chat.utilities import check_rate_limit, get_llm_service
from chat.models import ChatSession, ChatMessage, UploadedDocument

logger = logging.getLogger(__name__)
GENERIC_ERROR = "Something went wrong while processing your request."

# How many recent messages to load from the DB as LLM context.
# (LLMService trims further; loading the whole session would waste DB time.)
HISTORY_LOAD_LIMIT = 20


def get_or_create_session(user, session_id, first_message: str):
    """
    Returns (session, error_response).
    An existing session must belong to `user` and not be soft-deleted; otherwise a new one is created.
    """
    if session_id:
        session = ChatSession.objects.filter(id=session_id, user=user, is_deleted=False).first()
        if not session:
            return None, Response({"error": "Invalid session ID"}, status=status.HTTP_403_FORBIDDEN)
        return session, None
    title = first_message[:30] + "..." if len(first_message) > 30 else first_message
    return ChatSession.objects.create(user=user, title=title), None


def load_history(session) -> list[ChatMessageDTO]:
    """
    Loads the recent conversation from the DB (H6: never trust a client-supplied history).
    Must be called BEFORE the new user message is saved, so it is not duplicated.
    """
    recent = list(
        ChatMessage.objects.filter(session=session, is_deleted=False)
        .order_by("-created_at")[:HISTORY_LOAD_LIMIT]
    )
    recent.reverse()
    return [ChatMessageDTO(role=m.role, content=m.content) for m in recent]


def file_sha256(uploaded_file) -> str:
    """SHA-256 of an uploaded file, read in chunks so large files do not fill memory."""
    h = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        h.update(chunk)
    uploaded_file.seek(0)
    return h.hexdigest()


def delete_document(doc) -> None:
    """Deletes the DB row AND the file on disk (doc.delete() alone leaves the file behind)."""
    if doc.file:
        try:
            doc.file.delete(save=False)
        except OSError as e:
            logger.error(f"Failed to delete file for document {doc.id}: {e}")
    doc.delete()


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

    def generate_post_response(self, chat_request: ChatRequest, history: list[ChatMessageDTO], user_id: str):
        try:
            reply = async_to_sync(self.llm_service.generate_reply)(
                chat_request.message, history, str(user_id), chat_request.use_fast
            )
            return Response({"reply": reply})
        except Exception:
            logger.exception("Chat request failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        logger.info(f"User {request.user.id} started a chat session.")
        user_id = request.user.id
        try:
            # 🔥 SECURITY FIX: Use user_id instead of IP
            check_rate_limit(str(user_id), scope="chat")
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



        # 1. Create or get session (SECURITY FIX: Ensure it (must) belongs to the user)
        session, error = get_or_create_session(request.user, req.session_id, req.message)
        if error:
            return error

        # 2. H6 FIX: history comes from the DB, not from the request body
        history = load_history(session)

        # 3. Save User Message to DB
        ChatMessage.objects.create(session=session, role="user", content=req.message)

        # 4. Get AI Response (Call LLM Non-streaming)
        response = self.generate_post_response(req, history, user_id)

        # 5. Save AI Reply to DB
        if response.status_code == 200:
            ai_reply = response.data.get("reply", "")
            ChatMessage.objects.create(session=session, role="assistant", content=ai_reply)
            response.data["session_id"] = session.id

        return response

    def delete(self, request):
        try:
            user_id = request.user.id

            # 🔥 SECURITY FIX: Use user_id instead of IP
            # check_rate_limit(request.META.get("REMOTE_ADDR", "unknown"), scope="clear")
            check_rate_limit(str(user_id), scope="clear")
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            # 1. Purge ChromaDB (RAG memory and vectors)
            self.llm_service.clear_session(str(user_id))

            # 2. Purge physical files from disk (media/documents/user_<id>/)
            docs = UploadedDocument.objects.filter(user=request.user)
            for doc in docs:
                if doc.file and os.path.exists(doc.file.path):
                    try:
                        os.remove(doc.file.path)
                    except OSError as e:
                        logger.error(f"Failed to delete file {doc.file.path}: {e}")

            # 3. Delete DB records permanently (Hard Delete for GDPR)
            # Note: We use .delete() instead of .update(is_deleted=True) to fully remove data.
            ChatMessage.objects.filter(session__user=request.user).delete()
            ChatSession.objects.filter(user=request.user).delete()
            UploadedDocument.objects.filter(user=request.user).delete()

        except Exception:
            logger.exception("Clearing session failed")
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "All data (MySQL, Disk, ChromaDB) permanently deleted."})


class ChatStreamAPIView(ChatAPIView):
    """
    Streaming View for Chat API (SSE).
    Overrides the post method to handle streaming instead of JSON.
    """

    def post(self, request):
        try:
            user_id = request.user.id

            # 🔥 SECURITY FIX: Use user_id instead of IP
            # check_rate_limit(request.META.get("REMOTE_ADDR", "unknown"), scope="chat")
            check_rate_limit(str(user_id), scope="chat")

            req = ChatRequest(**request.data)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ValidationError as e:
            return Response({"detail": json.loads(e.json(include_url=False, include_input=False))},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Create DB Session or get existing one (must belong to the user)
        session, error = get_or_create_session(request.user, req.session_id, req.message)
        if error:
            return error

        # 🔥 SECURITY FIX (H6): Load history from DB instead of trusting the client
        history_list = load_history(session)

        # Save User Message
        ChatMessage.objects.create(session=session, role="user", content=req.message)

        service = self.llm_service

        async def event_gen():
            full_reply = ""
            try:
                # Send the new session ID to the frontend immediately
                yield f"data: {json.dumps({'session_id': session.id})}\n\n"

                # 🔥 FIX (H6): Pass the DB history to the service, never a client-supplied one
                async for delta in service.stream_reply(
                        req.message, history_list, str(user_id), req.use_fast
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

                # Fetch documents for this session
                documents = session.documents.all().values('id', 'filename', 'uploaded_at')

                return Response({
                    "id": session.id,
                    "title": session.title,
                    "messages": list(messages),
                    "documents": list(documents)
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
            # 🔥 SECURITY FIX: Verify the session belongs to the current user
            session = ChatSession.objects.filter(id=session_id, user=request.user).first()
            if not session:
                return Response({"error": "Session not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)

            # 1. Soft delete the specific session
            session.is_deleted = True
            session.save()

            # 2. Soft delete messages belonging to THAT session (Security Fix)
            ChatMessage.objects.filter(session=session).update(is_deleted=True)

            # Note: We do NOT call clear_session() here because it would delete ALL RAG data for the user.
            # RAG data is tied to the user, not the specific chat session.

            return Response({"message": "Chat deleted successfully."})
        else:
            # Soft delete all chats for the user
            ChatSession.objects.filter(user=request.user).update(is_deleted=True)
            ChatMessage.objects.filter(session__user=request.user).update(is_deleted=True)

            # If deleting ALL chats, it makes sense to also clear the RAG memory
            self.llm_service.clear_session(str(request.user.id))

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
            user_id = request.user.id
            upload_limit = getattr(settings, "UPLOAD_RATE_LIMIT", 5)

            # 🔥 SECURITY FIX: Use user_id instead of IP
            # check_rate_limit(request.META.get("REMOTE_ADDR", "unknown"), limit=upload_limit, scope="upload")
            check_rate_limit(str(user_id), limit=upload_limit, scope="upload")

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

        # 1. Reject duplicates (R5): same content already uploaded by this user
        file_hash = file_sha256(uploaded_file)
        existing = UploadedDocument.objects.filter(user=request.user, file_hash=file_hash).first()
        if existing:
            return Response({
                "detail": f"This file is already uploaded (as '{existing.filename}').",
                "document_id": existing.id,
                "filename": existing.filename,
            }, status=status.HTTP_409_CONFLICT)

        # 2. Get Session (if any)
        session_id = request.data.get("session_id")
        chat_session = None
        if session_id:
            chat_session = ChatSession.objects.filter(id=session_id, user=request.user, is_deleted=False).first()

        # 3. Create the Database Entry FIRST and let Django save the file
        # (Django will automatically use the 'user_directory_path' function from models.py)
        doc = UploadedDocument.objects.create(
            user=request.user,
            chat_session=chat_session,
            file=uploaded_file,  # Pass the file directly
            filename=safe_name,
            file_hash=file_hash,
        )

        # Now the file is saved at: media/documents/user_<id>/filename.ext
        file_path = doc.file.path

        try:
            # 4. Pass the saved file path to RAG Engine for processing
            result_message, chunk_count = self.llm_service.upload_document(file_path, safe_name, str(user_id))
        except Exception:
            logger.exception("Upload processing failed")
            # If processing fails, delete the file and the DB entry
            delete_document(doc)
            return Response({"detail": GENERIC_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if chunk_count == 0:
            # Nothing could be indexed (empty or unreadable file): do not keep a useless upload
            delete_document(doc)
            return Response({"detail": result_message}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # 5. M4 FIX: store the real chunk count returned by the RAG engine
        doc.chunk_count = chunk_count
        doc.save(update_fields=["chunk_count"])

        return Response({
            "message": result_message,
            "document_id": doc.id,  # download via the authenticated /api/download/<id> endpoint
            "filename": safe_name,
            "chunk_count": chunk_count,
        }, status=status.HTTP_200_OK)


class DownloadDocumentAPIView(APIView):
    """
    Secure endpoint to download a document.
    Ensures the user is the owner of the document.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        # Ensure the document belongs to the requesting user
        doc = get_object_or_404(UploadedDocument, id=document_id, user=request.user)

        try:
            # FileResponse streams the file efficiently
            return FileResponse(doc.file.open('rb'), as_attachment=True, filename=doc.filename)
        except FileNotFoundError:
            return Response({"error": "File not found on server."}, status=status.HTTP_404_NOT_FOUND)