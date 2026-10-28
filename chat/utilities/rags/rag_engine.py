import os
import chromadb
import numpy as np
from chromadb.utils import embedding_functions


class RAGEngine:
    """
    RAG Engine to handle text embedding, retrieval, and similarity checks.
    """

    def __init__(self):
        # Use Ollama's local embedding model
        self.embedding_fn = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name="nomic-embed-text"
        )

        # Initialize ChromaDB path
        self.chroma_path = "rag/rag_data/chroma_db"
        os.makedirs(self.chroma_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.chroma_path)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculates the cosine similarity between two texts.
        Useful for educational debugging (to see how close two sentences are).
        """
        # Get embeddings from Ollama
        emb1 = self.embedding_fn([text1])[0]
        emb2 = self.embedding_fn([text2])[0]

        # Calculate Cosine Similarity: (A.B) / (||A|| * ||B||)
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))