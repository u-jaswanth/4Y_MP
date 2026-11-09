from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    # Prior turns of THIS conversation, oldest first. Optional - the
    # backend now also keeps its own persisted history (see
    # ChatMessage / GET /chat/history), so this is only needed as a
    # same-request nudge; it's no longer the only place history lives.
    history: Optional[list[ChatTurn]] = None


class ChatResponse(BaseModel):
    answer: str
    scope: str
    patient_observations_used: int
    knowledge_chunks_used: int


class ChatHistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryOut(BaseModel):
    messages: list[ChatHistoryTurn]
