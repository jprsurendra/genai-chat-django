import os
import chromadb
import numpy as np
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


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

    def retrieve_similar_old(self, query: str, top_k: int = 2):
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

    def retrieve_similar(self, query: str, top_k: int = 3):
        """
        Retrieves the top_k most similar documents, filtering out previous questions.
        """
        # Fetch a larger pool of results to filter from
        results = self.collection.query(
            query_texts=[query],
            n_results=10  # Get 10 results
        )

        filtered_docs = []
        if results and results["documents"]:
            for doc in results["documents"][0]:
                # Filter out the previous questions
                # If the text ends with "?" and starts with "User:", ignore it
                if doc.startswith("User:") and doc.strip().endswith("?"):
                    continue
                filtered_docs.append(doc)

                # Stop when we have enough results
                if len(filtered_docs) >= top_k:
                    break

        return filtered_docs

    def process_and_store_file(self, file_path: str):
        """
        Reads a PDF or TXT file, splits it into chunks, and stores them in ChromaDB.
        """
        text = ""
        print("\n" + "=" * 60)
        print(f"#3: Full Document Upload (PDF/TXT)  ...")
        print(f"   🔍 Uploading file_path: '{file_path}'")
        print("=" * 60)

        # 1. Extract text based on file type
        if file_path.endswith(".pdf"):
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            return "Unsupported file format. Please upload PDF or TXT."

        if not text.strip():
            return "File is empty or could not be read."

        print(f"   text: '{text}'")
        print("-" * 60)

        # 2. Split text into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len
        )
        chunks = splitter.split_text(text)

        # 3. Store in ChromaDB
        # We use a unique ID for each chunk
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]

        self.collection.add(
            documents=chunks,
            ids=ids
        )
        print(f"   Successfully uploaded and embedded {len(chunks)} chunks from the document.")
        print("=" * 60)
        return f"Successfully uploaded and embedded {len(chunks)} chunks from the document."

    def store_chat_message(self, role: str, content: str):
        """
        Stores individual chat messages (user or assistant) into the Vector Store.
        This allows the AI to remember past conversations.
        """
        import uuid
        doc_id = str(uuid.uuid4())

        # Check if the message is a question or a statement
        is_question = content.strip().endswith("?")
        msg_type = "question" if is_question else "statement"

        # We format the text so it's clear who said what
        formatted_text = f"{role.capitalize()}: {content}"

        self.collection.add(
            documents=[formatted_text],
            ids=[doc_id],
            # metadatas=[{"role": role, "type": "chat_history"}]  # Metadata for filtering later
            metadatas=[{"role": role, "type": msg_type}]  # Save the type
        )
