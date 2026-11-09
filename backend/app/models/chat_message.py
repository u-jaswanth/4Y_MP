import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ChatMessage(Base):
    """
    One turn of a patient's conversation with the AI chatbot.

    Persisting this server-side (instead of only keeping it in the
    frontend's React state) is what gives the chatbot real memory -
    previously all context was lost on refresh/navigation because
    the frontend was the only place conversation history lived.
    """

    __tablename__ = "chat_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False
    )

    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
