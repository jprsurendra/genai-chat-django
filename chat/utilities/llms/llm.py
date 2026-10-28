from openai import AsyncOpenAI
from django.conf import settings
from chat.dtos import ChatMessage

from chat.utilities.rags.rag_engine import RAGEngine

class LLMService:
    """
    A Service class to handle all interactions with the Large Language Model (LLM).

    OOPS Concept Used: Encapsulation.
    This class encapsulates the client initialization, model selection,
    prompt building, and API calls into a single reusable unit.
    """

    def __init__(self):
        """
        Constructor: Initializes the OpenAI client and RAG Engine.
        """
        self.client, self.default_model = self._create_client()
        # Initializes RAG Engine
        self.rag_engine = RAGEngine()

    def _create_client(self) -> tuple[AsyncOpenAI, str]:
        """
        Private method to create the LLM client based on the .env settings.
        Supports both 'ollama' (local) and 'openai' (cloud).
        """
        if settings.LLM_PROVIDER == "ollama":
            return (
                AsyncOpenAI(base_url=settings.OLLAMA_BASE_URL, api_key="ollama"),
                settings.OLLAMA_MODEL,
            )
        return (
            AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
            settings.OPENAI_MODEL,
        )

    def _resolve_model(self, use_fast: bool = False) -> str:
        """
        Private method to select the correct model.
        If 'use_fast' is True and provider is Ollama, it returns the lightweight fast model.
        """
        if settings.LLM_PROVIDER == "ollama" and use_fast:
            return settings.OLLAMA_MODEL_FAST
        return self.default_model

    def _build_messages(self, user_message: str, history: list[ChatMessage]) -> list[dict]:
        """
        Private method to build the payload for the LLM.
        It combines the System Prompt, the RAG context, the last 10 turns of history, and the new user message.
        """
        # 1. Retrieve context from Vector Store (RAG)
        retrieved_docs = self.rag_engine.retrieve_similar(user_message, top_k=3)

        # <--- DEBUG PRINT --->
        print("\n" + "=" * 50)
        print(f"🔍 RAG DEBUG FOR: '{user_message}'")
        if retrieved_docs:
            for i, doc in enumerate(retrieved_docs):
                print(f"  Match {i + 1}: {doc}")
        else:
            print("  ❌ NO CONTEXT FOUND!")
        print("=" * 50 + "\n")
        # <--- END DEBUG --->

        # 2. Build the System Prompt with Context
        system_content = settings.SYSTEM_PROMPT

        # if retrieved_docs:
        #     context_text = "\n".join(retrieved_docs)
        #     system_content += (
        #         f"\n\nIMPORTANT: Use the following retrieved context to answer the user's question. "
        #         f"If the answer is not in the context, you can use your own knowledge, but prioritize the context.\n"
        #         f"--- CONTEXT START ---\n{context_text}\n--- CONTEXT END ---"
        #     )

        if retrieved_docs:
            context_text = "\n".join(retrieved_docs)
            # # Make the instruction stricter
            # system_content += (
            #     f"\n\nCRITICAL INSTRUCTION: Read the following context carefully and copy the exact words to answer the user. "
            #     f"Do NOT change any names or places.\n"
            #     f"--- CONTEXT START ---\n{context_text}\n--- CONTEXT END ---"
            # )
            # Update the instruction to be crystal clear (Ref: screenshot_003_004.png)
            system_content += (
                f"\n\nIMPORTANT: You are an AI assistant. The following context contains previous conversations. "
                f"When the user asks about 'my' (e.g., 'my favorite color'), they are referring to themselves (the User), NOT you (the AI). "
                f"Read the context carefully to find the user's personal details and answer accordingly.\n"
                f"--- CONTEXT START ---\n{context_text}\n--- CONTEXT END ---"
            )

        # 3. Create the messages list
        messages = [{"role": "system", "content": system_content}]

        # Keep only the last 10 messages to control token usage
        for m in history[-10:]:
            messages.append({"role": m.role, "content": m.content})

        messages.append({"role": "user", "content": user_message})
        return messages

    async def generate_reply(
        self, user_message: str, history: list[ChatMessage], use_fast: bool = False
    ) -> str:
        """
        Public method: Generates a complete, non-streaming reply from the LLM.
        Waits for the entire response to be generated before returning.
        """
        resp = await self.client.chat.completions.create(
            model=self._resolve_model(use_fast),
            messages=self._build_messages(user_message, history),
            temperature=0.7,
            max_tokens=800,
        )
        reply_text =  resp.choices[0].message.content or ""

        # Save both the user's message and AI's reply to the Vector Store
        self.rag_engine.store_chat_message("User", user_message)
        if reply_text:
            self.rag_engine.store_chat_message("AI", reply_text)

        return reply_text

    async def stream_reply(
        self, user_message: str, history: list[ChatMessage], use_fast: bool = False
    ):
        """
        Public method: Asynchronous Generator that yields token-by-token responses.
        Used for Server-Sent Events (SSE) streaming.
        """
        # Save the user's message immediately
        self.rag_engine.store_chat_message("User", user_message)

        full_reply = ""
        stream = await self.client.chat.completions.create(
            model=self._resolve_model(use_fast),
            messages=self._build_messages(user_message, history),
            temperature=0.7,
            max_tokens=800,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_reply += delta
                yield delta

        # After the stream finishes, save the full AI reply
        if full_reply:
            self.rag_engine.store_chat_message("AI", full_reply)

    # def debug_embeddings(self, user_message: str, sentences: list[str]):
    def debug_embeddings(self, user_message: str):
        """
        Educational print statements to show how embeddings work.
        """
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
            score = self.rag_engine.calculate_similarity(user_message, s)
            print(f"Similarity with '{s}': {score:.4f}")

        print("=" * 60 + "\n")

    def test_manual_vector_store(self, user_message: str):
        """
        Educational method to demonstrate storing and retrieving from the Vector Store.
        """
        # 1. Define a manual Knowledge Base
        knowledge_base = [
            "Python एक programming language है।",
            "Machine Learning AI की एक branch है।",
            "Delhi भारत की राजधानी है।",
            "RAG का मतलब Retrieval Augmented Generation है।",
            "Embeddings text को vectors में बदलते हैं।"
        ]
        print("\n" + "=" * 60)
        print(f"#2. Simple Vector Store (Manual)")

        # 2. Store these documents in ChromaDB (only if it's the first time)
        # We check if the collection is empty
        if self.rag_engine.collection.count() == 0:
            print("   [Vector Store is empty. Storing knowledge base...]")
            self.rag_engine.store_documents(knowledge_base)

        # 3. Retrieve the most similar documents for the user's query
        print(f"   🔍 RETRIEVING FROM VECTOR STORE FOR: '{user_message}'")
        print("=" * 60)
        retrieved_docs = self.rag_engine.retrieve_similar(user_message, top_k=2)

        print("Top Matches Found:")
        for i, doc in enumerate(retrieved_docs):
            print(f"  {i + 1}. {doc}")
        print("=" * 60 + "\n")

    def upload_document(self, file_path: str):
        """
        Passes the uploaded file to the RAG Engine for processing.
        """
        return self.rag_engine.process_and_store_file(file_path)