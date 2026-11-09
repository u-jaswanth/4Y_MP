import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AccessStatus:
    """Plain string constants rather than a DB enum - keeps adding a
    new status a one-line change instead of an ALTER TYPE migration."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    REVOKED = "revoked"


class AccessRequest(Base):
    """A doctor's request to read one patient's record, and the
    patient's decision on it.

    One row per request. Approving, denying or revoking never deletes
    the row - it moves `status` and stamps `decided_at` - so this same
    table backs three different screens:

      - the doctor's "Find patient" flow, which creates a PENDING row
      - the patient's "Doctor access" page, which lists PENDING rows
        to act on and APPROVED rows to revoke
      - the doctor's "My patients" list, which is just the APPROVED
        rows for that doctor

    Only one open row (pending or approved) is allowed per
    doctor/patient pair at a time - enforced in app/access code, not
    here, so a denied or revoked request never blocks trying again.
    """

    __tablename__ = "access_requests"

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

    # What the doctor typed in as the reason for the request - shown to
    # the patient before they decide.
    note = Column(Text, nullable=True)

    status = Column(String, nullable=False, default=AccessStatus.PENDING)

    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

    doctor = relationship("Doctor")
    patient = relationship("Patient")
