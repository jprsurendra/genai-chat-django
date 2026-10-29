import hashlib
import logging
import os
import re
import uuid

import chromadb
import numpy as np
from chromadb.utils import embedding_functions
from django.conf import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Regex to validate session IDs (8-64 characters, alphanumeric, dashes, underscores)
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def is_valid_session_id(session_id: str) -> bool:
    """Validates if the provided session ID matches the required format."""
    return bool(session_id) and bool(SESSION_ID_RE.match(session_id))


class RAGEngine:
    """
    RAG Engine to handle text embedding, retrieval, and document processing.
    Uses two separate ChromaDB collections: one for documents, one for chat memory.
    """
    DOCS_COLLECTION = "documents_v2"
    MEMORY_COLLECTION = "chat_memory_v2"
    DEMO_COLLECTION = "manual_knowledge_base"  # Used only for debugging/learning

    def __init__(self, embedding_fn=None, chroma_path=None, max_distance=None):
        # Use Ollama's local embedding model
        self.embedding_fn = embedding_fn or embedding_functions.OllamaEmbeddingFunction(
            url=settings.OLLAMA_EMBED_URL,
            model_name=settings.EMBED_MODEL,
        )

        # Maximum cosine distance allowed for a result to be considered relevant
        self.max_distance = settings.RAG_MAX_DISTANCE if max_distance is None else max_distance

        # Initialize ChromaDB storage
        self.chroma_path = str(chroma_path or settings.RAG_PATH)
        os.makedirs(self.chroma_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.chroma_path)

        # Create or get collections
        self.documents = self._collection(self.DOCS_COLLECTION)
        self.memory = self._collection(self.MEMORY_COLLECTION)

    def _collection(self, name: str):
        """Helper method to create/get a collection with cosine distance metric."""
        return self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    # =====================================================================
    # CORE PRODUCTION METHODS
    # =====================================================================

    def _query(self, collection, query: str, session_id: str, top_k: int) -> list[str]:
        """Internal method to query a collection and filter by session and distance."""
        if collection.count() == 0:
            return []

        res = collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"session_id": session_id},  # Ensure data isolation
            include=["documents", "distances"],
        )

        docs = (res.get("documents") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        # Only return documents that are within the allowed relevance distance
        return [d for d, dist in zip(docs, dists) if dist <= self.max_distance]


    def retrieve_documents(self, query: str, session_id: str, top_k: int = 3) -> list[dict]:
        """Retrieves relevant
        1. text chunks
            return self._query(self.documents, query, session_id, top_k)
        AND
        2. their metadata (filename, page)
        from uploaded documents."""
        if self.documents.count() == 0:
            return []

        res = self.documents.query(
            query_texts=[query],
            n_results=top_k,
            where={"session_id": session_id},
            include=["documents", "distances", "metadatas"], # Include metadata
        )

        docs = (res.get("documents") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]

        results = []
        for doc, dist, meta in zip(docs, dists, metas):
            if dist <= self.max_distance:
                results.append({
                    "text": doc,
                    "filename": meta.get("filename", "Unknown"),
                    "page": meta.get("page", 1)
                })
        return results

    def retrieve_memories(self, query: str, session_id: str, top_k: int = 3) -> list[str]:
        """Retrieves relevant past statements made by the user."""
        return self._query(self.memory, query, session_id, top_k)

    def process_and_store_file_old(self, file_path: str, session_id: str) -> str:
        """Reads a PDF/TXT file, chunks it, and stores embeddings in ChromaDB."""
        lower = file_path.lower()
        text = ""

        # Extract text based on file type
        if lower.endswith(".pdf"):
            reader = PdfReader(file_path)
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        elif lower.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            return "Unsupported file format. Please upload PDF or TXT."

        if not text.strip():
            return "File is empty or could not be read."

        # Split text into manageable chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, length_function=len)
        chunks = [c for c in splitter.split_text(text) if c.strip()]

        # Deterministic IDs prevent duplicate uploads of the same file
        ids = [hashlib.sha1(f"{session_id}:{c}".encode("utf-8")).hexdigest() for c in chunks]

        self.documents.upsert(
            documents=chunks,
            ids=ids,
            metadatas=[{"session_id": session_id}] * len(chunks),
        )
        return f"Successfully uploaded and embedded {len(chunks)} chunks from the document."

    def process_and_store_file(self, file_path: str, session_id: str) -> str:
        """Reads a PDF/TXT file, chunks it, and stores embeddings with metadata."""
        lower = file_path.lower()
        filename = os.path.basename(file_path)
        text = ""
        page_number = 1  # For TXT files

        if lower.endswith(".pdf"):
            reader = PdfReader(file_path)
            pages = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                # Add a hidden tag to track page numbers during chunking
                pages.append(f"[PAGE_{i + 1}]{page_text}")
            text = "\n".join(pages)
        elif lower.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            return "Unsupported file format. Please upload PDF or TXT."

        if not text.strip():
            return "File is empty or could not be read."

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, length_function=len)
        raw_chunks = splitter.split_text(text)

        chunks = []
        metadatas = []
        ids = []

        current_page = 1

        for chunk in raw_chunks:
            if not chunk.strip():
                continue

            # Extract page number if the tag is in this chunk
            page_match = re.search(r"\[PAGE_(\d+)\]", chunk)
            if page_match:
                current_page = int(page_match.group(1))
                # Remove the tag from the actual text shown to the LLM
                chunk = re.sub(r"\[PAGE_\d+\]", "", chunk).strip()

            if not chunk:
                continue

            chunks.append(chunk)
            metadatas.append({
                "session_id": session_id,
                "filename": filename,
                "page": current_page
            })
            ids.append(hashlib.sha1(f"{session_id}:{filename}:{current_page}:{chunk}".encode("utf-8")).hexdigest())

        self.documents.upsert(
            documents=chunks,
            ids=ids,
            metadatas=metadatas,
        )
        return f"Successfully uploaded and embedded {len(chunks)} chunks from {filename}."

    @staticmethod
    def is_memorable(content: str) -> bool:
        """We only remember statements, not questions."""
        text = content.strip()
        return bool(text) and not text.endswith("?")

    def store_user_message(self, content: str, session_id: str) -> bool:
        """Saves a user's statement into the chat memory collection."""
        if not self.is_memorable(content):
            return False

        self.memory.add(
            documents=[f"User said: {content.strip()[:1000]}"],
            ids=[str(uuid.uuid4())],
            metadatas=[{"session_id": session_id}],
        )
        return True

    def delete_session(self, session_id: str) -> None:
        """Deletes all documents and memories associated with a specific session."""
        for col in (self.documents, self.memory):
            col.delete(where={"session_id": session_id})

    # =====================================================================
    # ⚠️ DEBUGGING & EDUCATIONAL METHODS (NOT FOR PRODUCTION USE)
    # =====================================================================
    # The following methods are kept for learning, testing, and debugging.
    # They should NOT be called in the main chat flow (LLMService / Views).
    # =====================================================================

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        [DEBUGGING ONLY] Calculates cosine similarity between two texts.
        Useful to see how close two sentences are in vector space.
        """
        # Get embeddings from Ollama
        emb1 = self.embedding_fn([text1])[0]
        emb2 = self.embedding_fn([text2])[0]

        # Calculate Cosine Similarity: (A.B) / (||A|| * ||B||)
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

    def demo_collection(self):
        """
        [DEBUGGING ONLY] Returns a separate collection for manual testing.
        This ensures demo data does not pollute the real user collections.
        """
        return self._collection(self.DEMO_COLLECTION)

    def store_documents(self, documents: list[str]):
        """
        [DEBUGGING ONLY] Stores manual test documents into the DEMO collection.
        Useful for testing retrieval without uploading a real PDF file.
        """
        demo_col = self.demo_collection()

        # Create simple IDs for the documents
        ids = [f"doc_{i}" for i in range(len(documents))]

        demo_col.add(
            documents=documents,
            ids=ids
        )
        print(f"✅ Successfully stored {len(documents)} documents in Demo Vector Store.")

    def retrieve_similar(self, query: str, top_k: int = 3):
        """
        [DEBUGGING ONLY] Retrieves top_k documents from the DEMO collection.
        Useful for testing vector search manually.
        """
        demo_col = self.demo_collection()

        if demo_col.count() == 0:
            return []

        results = demo_col.query(
            query_texts=[query],
            n_results=top_k
        )

        if results and results["documents"]:
            return results["documents"][0]

        return []

    def debug_embeddings(self, user_message: str, sentences: list[str] = None):
        """
        [DEBUGGING ONLY] Prints similarity scores to the terminal.
        Useful for understanding how the embedding model behaves with different sentences.
        """
        if sentences is None:
            sentences = [
                "मुझे चाय पसंद है",
                "I love tea",
                "मुझे कॉफ़ी बहुत पसंद है",
                "The weather is nice today"
            ]

        print("\n" + "=" * 60)
        print(f"#1. Embeddings Basic Example ...")
        print(f"   🔍 EMBEDDING SIMILARITY FOR USER INPUT: '{user_message}'")
        print("=" * 60)

        for s in sentences:
            score = self.calculate_similarity(user_message, s)
            print(f"Similarity with '{s}': {score:.4f}")

        print("=" * 60 + "\n")