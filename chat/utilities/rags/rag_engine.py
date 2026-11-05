import hashlib
import logging
import os
import re
import uuid
import json  # 🔥 NEW: For storing JSON in Redis
import redis  # 🔥 NEW: For caching

import chromadb
import numpy as np
from chromadb.utils import embedding_functions
from django.conf import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# Import BM25 for Hybrid Search
from rank_bm25 import BM25Okapi

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

        # 🔥 NEW: Initialize Redis for Semantic Caching
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, "REDIS_HOST", "localhost"),
                port=getattr(settings, "REDIS_PORT", 6379),
                db=getattr(settings, "REDIS_DB", 0),
                decode_responses=True,
                socket_timeout=1.0
            )
        except Exception as e:
            logger.error(f"Redis connection failed for caching: {e}")
            self.redis_client = None

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

    def _tokenize(self, text: str) -> list[str]:
        """
        Improved tokenizer:
        1. Converts to lowercase.
        2. Extracts only words (ignores punctuation).
        3. Ignores short words (<= 2 chars) like 'is', 'the', '2', '+'.
        """
        # 🔥 FIX (H1): Match words in both English and Hindi (Devanagari block)
        # \w+ in Python misses Hindi vowel signs, so we explicitly include the Devanagari unicode range
        words = re.findall(r'[\w\u0900-\u097F]+', text.lower())
        return [w for w in words if len(w) > 2]

    def _query(self, collection, query: str, session_id: str, top_k: int) -> list[dict]:
        """
        Hybrid Search: Combines Vector Search (semantic) with BM25 (keyword).
        """
        if collection.count() == 0:
            return []

        # 1. Get ALL documents for this user from ChromaDB (to build the BM25 index)
        all_res = collection.get(
            where={"session_id": session_id},
            include=["documents", "metadatas"],
            limit=1000
        )
        all_docs = all_res.get("documents", [])
        all_metas = all_res.get("metadatas", [])

        if not all_docs:
            return []

        # 2. Build BM25 Index (Using the improved tokenizer)
        tokenized_corpus = [self._tokenize(doc) for doc in all_docs]
        # bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = self._tokenize(query)

        # 🔥 FIX (H1): Prevent ZeroDivisionError if all tokens are empty
        if not any(tokenized_corpus) or not tokenized_query:
            bm25_scores = [0.0] * len(all_docs)
        else:
            bm25 = BM25Okapi(tokenized_corpus)
            bm25_scores = bm25.get_scores(tokenized_query)

        # 3. Get Vector Search Scores from ChromaDB (Fetch more candidates for better hybrid mix)
        vector_res = collection.query(
            query_texts=[query],
            n_results=max(top_k * 3, 10),
            where={"session_id": session_id},
            include=["documents", "distances", "metadatas"],
        )

        vector_docs = (vector_res.get("documents") or [[]])[0]
        vector_dists = (vector_res.get("distances") or [[]])[0]
        vector_metas = (vector_res.get("metadatas") or [[]])[0]

        # 4. Combine Scores
        combined_results = []

        for i, doc in enumerate(all_docs):
            if doc in vector_docs:
                idx = vector_docs.index(doc)
                vector_dist = vector_dists[idx]
                meta = vector_metas[idx]
            else:
                vector_dist = 1.0
                meta = all_metas[i]

            # Normalize BM25 score
            normalized_bm25 = min(bm25_scores[i] / 5.0, 1.0) if bm25_scores[i] > 0 else 0.0

            # Convert distance to similarity (0 to 1)
            vector_score = 1.0 - vector_dist

            # Hybrid Score (50% Vector, 50% BM25)
            hybrid_score = (0.5 * vector_score) + (0.5 * normalized_bm25)

            combined_results.append({
                "text": doc,
                "filename": meta.get("filename", "Memory"),
                "page": meta.get("page", 1),
                "hybrid_score": hybrid_score,
                "vector_dist": vector_dist
            })

        # 5. Sort by Hybrid Score
        combined_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # 🔥 DEBUG: Print top 3 scores
        # print("\n[DEBUG] Top Hybrid Scores:")
        # for r in combined_results[:3]:
        #     print(
        #         f" - Score: {r['hybrid_score']:.4f} | Vector Dist: {r['vector_dist']:.4f} | Text: {r['text'][:30]}...")

        # 6. Filter and return top_k
        final_results = []
        for res in combined_results[:top_k]:
            # Strict Filter: If hybrid score is too low, reject it.
            if res["hybrid_score"] < 0.35:
                # print(f"   [DEBUG] Rejected with score {res['hybrid_score']:.4f}")
                continue

            final_results.append({
                "text": res["text"],
                "filename": res["filename"],
                "page": res["page"]
            })

        return final_results

    def retrieve_documents(self, query: str, session_id: str, top_k: int = 3) -> list[dict]:
        """Retrieves relevant text chunks and their metadata (filename, page) from uploaded documents."""
        return self._query(self.documents, query, session_id, top_k)

    def retrieve_memories(self, query: str, session_id: str, top_k: int = 3) -> list[dict]:
        """Retrieves relevant past statements made by the user."""
        return self._query(self.memory, query, session_id, top_k)

    def process_and_store_file(self, file_path: str, original_filename: str, user_id: str) -> str:
        """Reads a PDF/TXT file, chunks it, and stores embeddings with metadata."""
        lower = file_path.lower()
        filename = original_filename  # Use the original filename passed from the view

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
                "session_id": user_id,  # We use user_id as session_id for RAG
                "filename": filename,
                "page": current_page
            })
            # Generate a unique ID based on user, filename, page, and content
            ids.append(hashlib.sha1(f"{user_id}:{filename}:{current_page}:{chunk}".encode("utf-8")).hexdigest())

        # Upsert (Update or Insert) to ChromaDB
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
            metadatas=[{
                "session_id": session_id,
                "filename": "Chat History",
                "page": 1
            }],
        )
        return True

    def delete_session(self, session_id: str) -> None:
        """Deletes all documents and memories associated with a specific session."""
        for col in (self.documents, self.memory):
            col.delete(where={"session_id": session_id})

    # =====================================================================
    # 🔥 NEW: SEMANTIC CACHING METHODS
    # =====================================================================

    def _get_query_embedding(self, query: str) -> list[float]:
        """Generates a vector for the query string."""
        return self.embedding_fn([query])[0]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculates similarity between two vectors."""
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    def check_cache(self, query: str, session_id: str) -> str | None:
        """
        Checks if a similar query has been answered before.
        Returns the cached answer if similarity > threshold.
        """
        if self.redis_client is None:
            return None

        try:
            # 1. Get embedding for the new query
            query_vec = self._get_query_embedding(query)

            # 2. Get all cached queries for this session
            cache_key = f"cache:semantic:{session_id}"
            cached_items = self.redis_client.hgetall(cache_key)

            best_match = None
            highest_similarity = 0.0

            # 3. Compare with all cached queries
            for cached_query, cached_data in cached_items.items():
                data = json.loads(cached_data)
                cached_vec = data["embedding"]

                similarity = self._cosine_similarity(query_vec, cached_vec)

                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = data["answer"]

            # 4. If similarity is high enough, return the cached answer
            threshold = getattr(settings, "SIMILARITY_THRESHOLD", 0.95)
            if highest_similarity >= threshold:
                logger.info(f"⚡ Cache Hit! Similarity: {highest_similarity:.4f}")
                return best_match

        except Exception as e:
            logger.error(f"Cache check failed: {e}")

        return None

    def save_to_cache(self, query: str, answer: str, session_id: str):
        """Saves the query, its embedding, and the answer to Redis."""
        if self.redis_client is None:
            return

        try:
            query_vec = self._get_query_embedding(query)
            cache_key = f"cache:semantic:{session_id}"
            ttl = getattr(settings, "CACHE_TTL", 86400)

            # Store as a JSON string
            cache_data = json.dumps({
                "embedding": query_vec,
                "answer": answer
            })

            self.redis_client.hset(cache_key, query, cache_data)
            self.redis_client.expire(cache_key, ttl)
            logger.info(f"💾 Saved to Cache: '{query}'")

        except Exception as e:
            logger.error(f"Cache save failed: {e}")

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