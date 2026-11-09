import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    hospital = "hospital"
    doctor = "doctor"
    patient = "patient"


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.patient)

    # ------------------------------------------------------------
    # PORTAL LOGIN ID
    # ------------------------------------------------------------
    # Patients sign themselves up and log in with their email, so this
    # stays NULL for them.
    #
    # Hospitals and doctors do not sign themselves up - an admin issues
    # a hospital account, and a hospital issues its doctors' accounts.
    # Those accounts get a short, printable ID (HOSP-K7M2Q4 /
    # DOC-P4X9R2) which is what the person is actually handed and what
    # they type into the login box. See app/auth/credentials.py.
    #
    # Login accepts either this or the email, so nothing about the
    # existing patient flow changes.
    login_id = Column(String, unique=True, index=True, nullable=True)

    # ------------------------------------------------------------
    # FIRST-LOGIN PASSWORD CHANGE
    # ------------------------------------------------------------
    # True on every account created *for* someone with a generated
    # temporary password. While it is True, the token still works but
    # the UI sends the person straight to /change-password, and the
    # portal endpoints refuse to answer - so a temporary password can
    # never be left in place. Cleared by POST /auth/change-password.
    must_change_password = Column(
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
