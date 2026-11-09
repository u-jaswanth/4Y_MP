import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DoctorOut(BaseModel):
    id: uuid.UUID
    full_name: str
    gender: Optional[str] = None
    specialty: str
    qualification: Optional[str] = None
    experience_years: int = 0
    hospital: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    consultation_fee: Optional[int] = None
    rating: float = 0.0
    reviews_count: int = 0
    next_available: Optional[str] = None
    available_days: Optional[str] = None
    handles_emergencies: bool = False

    # Derived on the model.
    focus_list: list[str] = Field(default_factory=list)
    language_list: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DoctorMatch(BaseModel):
    doctor: DoctorOut
    match_score: int
    distance_km: Optional[float] = None
    distance_label: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)
    is_primary_specialty: bool = False


class RecommendationRequest(BaseModel):
    concern: str
    symptoms: str = Field(min_length=5, max_length=2000)
    duration: str
    severity: str
    area: str
    city: str = "Hyderabad"


class RecommendationOut(BaseModel):
    # What the AI understood from the form.
    case_summary: str
    specialties: list[str]
    urgency: str
    red_flags: list[str] = Field(default_factory=list)
    questions_for_doctor: list[str] = Field(default_factory=list)
    before_the_visit: list[str] = Field(default_factory=list)
    ai_reading_used: bool = False

    # Who to see.
    matches: list[DoctorMatch] = Field(default_factory=list)


class OptionsOut(BaseModel):
    concerns: list[dict]
    durations: list[dict]
    severities: list[dict]
    cities: list[str]
    areas: list[str]


class DoctorSelfOut(BaseModel):
    """A doctor's own profile, for the doctor portal.

    Deliberately read-only. A doctor can see exactly what patients see
    about them plus their own contact details; corrections go through
    the hospital that added them, which is where the record is owned.
    """

    id: uuid.UUID
    login_id: Optional[str] = None

    full_name: str
    gender: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    specialty: str
    qualification: Optional[str] = None
    experience_years: int = 0
    focus_list: list[str] = Field(default_factory=list)
    language_list: list[str] = Field(default_factory=list)

    hospital: Optional[str] = None
    hospital_phone: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None

    consultation_fee: Optional[int] = None
    rating: float = 0.0
    reviews_count: int = 0

    available_days: Optional[str] = None
    next_available: Optional[str] = None
    handles_emergencies: bool = False

    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
