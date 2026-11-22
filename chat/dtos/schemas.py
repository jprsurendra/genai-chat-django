from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    DTO (Data Transfer Object) for a single message.
    Only 'user' and 'assistant' roles are allowed from the client.
    Allowing 'system' would let a user override the server's system prompt (Security Risk).
    """

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    """
    DTO for the incoming POST request payload for chatting.
    Enforces message length.

    Note (H6): there is deliberately no `history` field. The conversation history is
    always loaded from the database on the server; a client-supplied history could be
    forged (for example fake "assistant" turns). Extra fields sent by old clients are ignored.
    """

    message: str = Field(..., min_length=1, max_length=4000)
    use_fast: bool = False
    session_id: int | None = None


class ChatResponse(BaseModel):
    """
    DTO for the outgoing non-streaming response.
    """

    reply: str
