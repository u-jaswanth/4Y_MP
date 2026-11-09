import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class DoctorChatMessage(Base):
    """One turn of a doctor's "Ask about this patient" conversation.

    Deliberately its own table rather than reusing ChatMessage: a
    patient's ChatMessage rows are keyed by patient_id alone because
    there is only ever one asker (the patient themself). Here the same
    patient can be asked about by several doctors with active access,
    each of whom should see only their own conversation - so a row is
    keyed by the (doctor_id, patient_id) pair.
    """

    __tablename__ = "doctor_chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    doctor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )

    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
