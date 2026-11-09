import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class HospitalCreate(BaseModel):
    """What the admin fills in to bring a hospital onto the platform."""

    name: str = Field(min_length=2, max_length=160)
    registration_number: Optional[str] = Field(default=None, max_length=80)
    hospital_type: Optional[str] = Field(default=None, max_length=60)

    address: Optional[str] = Field(default=None, max_length=300)

    # `area` is picked from app/doctors/locations.py, not typed freely -
    # it is what the recommender turns into coordinates, so a typo here
    # would quietly cost this hospital's doctors their distance score.
    area: str
    city: str = "Hyderabad"
    pincode: Optional[str] = Field(default=None, max_length=12)

    phone: Optional[str] = Field(default=None, max_length=20)
    email: EmailStr

    contact_person: Optional[str] = Field(default=None, max_length=120)
    contact_phone: Optional[str] = Field(default=None, max_length=20)

    bed_count: Optional[int] = Field(default=None, ge=0, le=10000)
    emergency_services: bool = False


class HospitalOut(BaseModel):
    id: uuid.UUID
    login_id: str

    name: str
    registration_number: Optional[str] = None
    hospital_type: Optional[str] = None

    address: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None

    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None

    bed_count: Optional[int] = None
    emergency_services: bool = False
    is_active: bool = True

    created_at: Optional[datetime] = None

    # Filled in by the route, not the ORM.
    doctor_count: int = 0
    password_changed: bool = False

    class Config:
        from_attributes = True


class IssuedCredentials(BaseModel):
    """Shown once, on the screen that created the account.

    The password is not stored anywhere in readable form, so this
    response is the only time it exists outside the person's hands. The
    admin screen says as much before it disappears.
    """

    login_id: str
    temporary_password: str
    must_change_password: bool = True


class HospitalCreated(BaseModel):
    hospital: HospitalOut
    credentials: IssuedCredentials


class AdminStats(BaseModel):
    hospitals: int = 0
    doctors: int = 0
    patients: int = 0

    # Doctors with no owning hospital, i.e. the seeded sample rows that
    # the recommendation page is still ranking.
    sample_doctors: int = 0
