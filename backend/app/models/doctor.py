import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Doctor(Base):
    """A doctor in the directory.

    Two kinds of row live here, and the recommender cannot tell them
    apart - which is the point:

      1. Seeded sample doctors (app/doctors/seed_data.py). These have
         `hospital_id` and `user_id` NULL: nobody owns them and nobody
         can log in as them. They exist so the recommendation page has
         something to rank during development.

      2. Real doctors added by a hospital through its portal. These
         carry `hospital_id`, a `user_id` they log in with, and a
         `login_id` printed on their credentials slip.

    Because both kinds fill in the same columns, switching the
    recommendation page from sample data to real data is not a code
    change - it is hospitals adding doctors, and then deleting the
    seeded rows. The columns the ranking actually reads are
    `specialty`, `focus_areas`, `latitude`/`longitude`, `rating`,
    `reviews_count`, `experience_years`, `next_available` and
    `handles_emergencies`; the hospital doctor form collects every one
    of them except the two ratings columns, which have to be earned
    from patient feedback rather than typed in by the hospital.
    """

    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Stable key from the seed file, so re-seeding updates rows instead
    # of creating duplicates. Hospital-created doctors get a generated
    # slug (name + short suffix) so the column stays unique either way.
    slug = Column(String, unique=True, nullable=False, index=True)

    # ------------------------------------------------------------
    # OWNERSHIP AND LOGIN (NULL for seeded sample doctors)
    # ------------------------------------------------------------

    hospital_id = Column(
        UUID(as_uuid=True),
        ForeignKey("hospitals.id"),
        nullable=True,
        index=True,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=True,
    )

    login_id = Column(String, unique=True, index=True, nullable=True)

    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    # ------------------------------------------------------------
    # PROFILE
    # ------------------------------------------------------------

    full_name = Column(String, nullable=False)
    gender = Column(String, nullable=True)

    specialty = Column(String, nullable=False, index=True)
    qualification = Column(String, nullable=True)
    experience_years = Column(Integer, default=0)

    # Comma-separated conditions this doctor is known for. Matched
    # against the triage output to break ties within a specialty.
    focus_areas = Column(Text, nullable=True)

    # Hospital NAME, kept as plain text so seeded rows (which have no
    # hospital_id) still read correctly. For hospital-created doctors
    # this is filled in from the owning hospital.
    hospital = Column(String, nullable=True)
    area = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    consultation_fee = Column(Integer, nullable=True)
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)

    languages = Column(String, nullable=True)
    available_days = Column(String, nullable=True)
    next_available = Column(String, nullable=True)

    # Whether the hospital runs a 24x7 emergency department - used to
    # rank for severe cases.
    handles_emergencies = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    hospital_record = relationship("Hospital", back_populates="doctors")

    # --------------------------------------------------------------

    @property
    def focus_list(self) -> list[str]:
        if not self.focus_areas:
            return []
        return [item.strip() for item in self.focus_areas.split(",") if item.strip()]

    @property
    def language_list(self) -> list[str]:
        if not self.languages:
            return []
        return [item.strip() for item in self.languages.split(",") if item.strip()]
