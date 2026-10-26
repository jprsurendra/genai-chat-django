from pydantic import BaseModel, Field
from typing import Literal

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    use_fast: bool = False

class ChatResponse(BaseModel):
    reply: str