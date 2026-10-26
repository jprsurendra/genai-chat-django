from openai import AsyncOpenAI
from django.conf import settings
from .schemas import ChatMessage

def _make_client() -> tuple[AsyncOpenAI, str]:
    if settings.LLM_PROVIDER == "ollama":
        return (
            AsyncOpenAI(base_url=settings.OLLAMA_BASE_URL, api_key="ollama"),
            settings.OLLAMA_MODEL,
        )
    return (
        AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
        settings.OPENAI_MODEL,
    )

client, _default_model = _make_client()

def resolve_model(use_fast: bool = False) -> str:
    if settings.LLM_PROVIDER == "ollama" and use_fast:
        return settings.OLLAMA_MODEL_FAST
    return _default_model

def _build_messages(user_message: str, history: list[ChatMessage]) -> list[dict]:
    messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}]
    for m in history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_message})
    return messages

async def generate_reply(
    user_message: str, history: list[ChatMessage], use_fast: bool = False
) -> str:
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