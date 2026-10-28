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

        # Create or get a collection to store our manual documents
        self.collection = self.client.get_or_create_collection(
            name="manual_knowledge_base",
            embedding_function=self.embedding_fn
        )

    # 1. What is Embeddings? (Basic Example). calculate_similarity(...)
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


    #2. Simple Vector Store (Manual): store_documents(...), retrieve_similar(...)
    def store_documents(self, documents: list[str]):
        """
        Stores a list of documents into the ChromaDB Vector Store.
        """
        # Create simple IDs for the documents
        ids = [f"doc_{i}" for i in range(len(documents))]

        # Add to ChromaDB (it will automatically embed them using the embedding_fn)
        self.collection.add(
            documents=documents,
            ids=ids
        )
        print(f"✅ Successfully stored {len(documents)} documents in Vector Store.")

    def retrieve_similar(self, query: str, top_k: int = 2):
        """
        Retrieves the top_k most similar documents from the Vector Store.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

        # ChromaDB returns a list of lists (one list per query)
        if results and results["documents"]:
            return results["documents"][0]
        return []
