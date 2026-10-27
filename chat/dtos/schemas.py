from pydantic import BaseModel, Field
from typing import Literal

class ChatMessage(BaseModel):
    """
    DTO (Data Transfer Object) for a single message.
    Validates that the role is strictly one of the allowed values.
    """
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    """
    DTO for the incoming POST request payload.
    Enforces rules like message length (1 to 4000 chars) and sets a default empty history.
    """
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    use_fast: bool = False

class ChatResponse(BaseModel):
    """
    DTO for the outgoing non-streaming response.
    Standardizes the JSON output.
    """
    reply: str