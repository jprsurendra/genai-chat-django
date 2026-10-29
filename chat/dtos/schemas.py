from pydantic import BaseModel, Field
from typing import Literal

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
    Enforces message length and caps the history size to prevent token overflow.
    """
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)
    use_fast: bool = False

class ChatResponse(BaseModel):
    """
    DTO for the outgoing non-streaming response.
    """
    reply: str