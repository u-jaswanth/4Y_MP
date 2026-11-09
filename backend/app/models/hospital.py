import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Hospital(Base):
    """A hospital, created by the admin.

    One hospital owns one `users` row (role=hospital) - that row holds
    the password, this row holds everything about the institution. The
    doctors a hospital adds point back here through
    `doctors.hospital_id`.

    `latitude` / `longitude` are filled in from `area` on create (see
    app/doctors/locations.py) so that every doctor this hospital adds
    lands on the same distance map the recommender already uses.
    """

    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    # Mirrors users.login_id. Duplicated here so the admin's hospital
    # list can show the ID without joining.
    login_id = Column(String, unique=True, index=True, nullable=False)

    # ------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------

    name = Column(String, nullable=False)
    registration_number = Column(String, nullable=True)
    hospital_type = Column(String, nullable=True)

    # ------------------------------------------------------------
    # WHERE
    # ------------------------------------------------------------

    address = Column(String, nullable=True)
    area = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True, index=True)
    pincode = Column(String, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # ------------------------------------------------------------
    # CONTACT
    # ------------------------------------------------------------

    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    # ------------------------------------------------------------
    # CAPABILITY
    # ------------------------------------------------------------

    bed_count = Column(Integer, nullable=True)

    # Inherited as the default for every doctor added here, because
    # `handles_emergencies` on a doctor is really a fact about the
    # hospital they sit in. The recommender reads it when ranking
    # urgent cases.
    emergency_services = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    doctors = relationship("Doctor", back_populates="hospital_record")
