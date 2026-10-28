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
        Constructor: Initializes the OpenAI client, RAG Engine and sets the default model.
        Since this is called once when the class is instantiated,
        we don't waste resources creating a new client on every request.
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
        It combines the System Prompt, the last 10 turns of history, and the new user message.
        """
        messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}]
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
        return resp.choices[0].message.content or ""

    async def stream_reply(
        self, user_message: str, history: list[ChatMessage], use_fast: bool = False
    ):
        """
        Public method: Asynchronous Generator that yields token-by-token responses.
        Used for Server-Sent Events (SSE) streaming.
        """
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
                yield delta

    def debug_embeddings(self, user_message: str, sentences: list[str]):
        """
        Educational print statements to show how embeddings work in the terminal.
        # Argument 'sentences' : These sentences are intentionally in Hindi and English to test cross-language similarity
        """

        print("\n" + "=" * 60)
        print(f"🔍 EMBEDDING SIMILARITY FOR USER INPUT: '{user_message}'")
        print("=" * 60)

        for s in sentences:
            score = self.rag_engine.calculate_similarity(user_message, s)
            print(f"Similarity with '{s}': {score:.4f}")

        print("=" * 60 + "\n")

    # ... (Keep your existing methods below: _resolve_model, _build_messages, generate_reply, stream_reply)