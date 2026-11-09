import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    full_name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    mobile = Column(String, nullable=True)

    # ------------------------------------------------------------
    # HEALTH ID
    # ------------------------------------------------------------
    # A 12-digit ID, generated once at registration (see
    # app/auth/credentials.py::generate_health_id), that the patient
    # hands to a hospital so its staff can find their account and
    # upload a report to it - see app/hospitals/routes.py. Nullable so
    # a patient row created before this column existed doesn't break;
    # GET /auth/patient/profile assigns one on first read if it's
    # still empty.
    health_id = Column(String, unique=True, index=True, nullable=True)

    aadhaar_number = Column(String, nullable=True)
    aadhaar_photo_path = Column(String, nullable=True)
    aadhaar_consent = Column(Boolean, default=False)

    # Optional off-site mirror of the Aadhaar photo (see
    # app/core/cloudinary_client.py). aadhaar_photo_path above remains
    # the source of truth on disk - these are purely additive.
    aadhaar_photo_url = Column(String, nullable=True)
    aadhaar_photo_public_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ------------------------------------------------------------
    # CACHED AI HEALTH SUMMARY
    # ------------------------------------------------------------
    # Generated ONCE, whenever a report finishes analyzing (see
    # app/reports/summary_service.py), not on every dashboard load.
    # GET /reports/summary just reads these columns back - it never
    # calls Gemini itself unless this cache is empty.
    ai_summary = Column(Text, nullable=True)
    ai_summary_observation_count = Column(Integer, nullable=True)
    ai_summary_reports_analyzed = Column(Integer, nullable=True)
    ai_summary_generated_at = Column(DateTime, nullable=True)

    user = relationship("User")
    reports = relationship("Report", back_populates="patient")
