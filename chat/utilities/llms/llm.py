from openai import AsyncOpenAI
from django.conf import settings
from chat.dtos import ChatMessage

def _make_client() -> tuple[AsyncOpenAI, str]:
    """
    Factory function to create the LLM client based on the .env settings.
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

# Initialize the client once when the module is loaded
client, _default_model = _make_client()

def resolve_model(use_fast: bool = False) -> str:
    """
    Selects the model. If 'use_fast' is True and provider is Ollama,
    it returns the lightweight fast model (e.g., qwen).
    """
    if settings.LLM_PROVIDER == "ollama" and use_fast:
        return settings.OLLAMA_MODEL_FAST
    return _default_model

def _build_messages(user_message: str, history: list[ChatMessage]) -> list[dict]:
    """
    Builds the payload for the LLM.
    Includes the System Prompt, the last 10 turns of history (to save tokens),
    and the current user message.
    """
    messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}]
    for m in history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_message})
    return messages

async def generate_reply(
    user_message: str, history: list[ChatMessage], use_fast: bool = False
) -> str:
    """
    Generates a complete, non-streaming reply from the LLM.
    Waits for the entire response to be generated before returning.
    """
    resp = await client.chat.completions.create(
        model=resolve_model(use_fast),
        messages=_build_messages(user_message, history),
        temperature=0.7,
        max_tokens=800,
    )
    return resp.choices[0].message.content or ""

async def stream_reply(
    user_message: str, history: list[ChatMessage], use_fast: bool = False
):
    """
    Asynchronous Generator that yields token-by-token responses from the LLM.
    Yields chunks as they arrive from the API (used for SSE streaming).
    """
    stream = await client.chat.completions.create(
        model=resolve_model(use_fast),
        messages=_build_messages(user_message, history),
        temperature=0.7,
        max_tokens=800,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta