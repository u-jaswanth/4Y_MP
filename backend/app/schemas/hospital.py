import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.admin import IssuedCredentials
from app.schemas.report import ReportOut


class HospitalProfileOut(BaseModel):
    """What a hospital sees about itself in its own portal."""

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

    created_at: Optional[datetime] = None
    doctor_count: int = 0

    class Config:
        from_attributes = True


class PatientLookupOut(BaseModel):
    """What hospital staff see after typing in a patient's Health ID -
    just enough to confirm it's the right person before uploading
    anything to their account.
    """

    health_id: str
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None

    class Config:
        from_attributes = True


class HospitalReportOut(ReportOut):
    """A report as the hospital that just uploaded it sees it back.

    Same shape as the patient's own ReportOut, plus which patient it
    went to - the hospital-side upload tab lists what it uploaded this
    session across possibly more than one patient.
    """

    patient_health_id: str
    patient_full_name: str


class DoctorCreate(BaseModel):
    """Everything a hospital fills in to add one doctor.

    The field list is not arbitrary - it is exactly what
    app/doctors/recommender.py reads when it ranks, so that a doctor
    added here can be scored the same way the seeded sample doctors
    are:

        specialty            50 points   required
        focus_areas          up to 6     matched against the patient's
                                         own words, so worth filling in
        area                 20 points   becomes lat/lng, distance
        experience_years     10 points
        next_available        5 points   "Today, 6:30 PM" scores; a
                                         date next week does not
        handles_emergencies   8 points   only for urgent cases

    `rating` and `reviews_count` are the one part of the ranking a
    hospital cannot set. They stay at 0 until there is real patient
    feedback to fill them with, which costs a new doctor up to 15
    points against the seeded rows - the honest outcome, given the
    seeded ratings are invented.
    """

    # ---- identity -------------------------------------------------
    full_name: str = Field(min_length=2, max_length=120)
    gender: Optional[str] = Field(default=None, max_length=20)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)

    # ---- practice -------------------------------------------------
    specialty: str
    qualification: Optional[str] = Field(default=None, max_length=200)
    experience_years: int = Field(default=0, ge=0, le=70)

    # Comma-separated: "chest pain, palpitations, blood pressure".
    focus_areas: Optional[str] = Field(default=None, max_length=600)

    consultation_fee: Optional[int] = Field(default=None, ge=0, le=100000)
    languages: Optional[str] = Field(default=None, max_length=200)

    # ---- availability ---------------------------------------------
    available_days: Optional[str] = Field(default=None, max_length=100)
    next_available: Optional[str] = Field(default=None, max_length=100)

    # ---- where ----------------------------------------------------
    # Defaults to the hospital's own area when left empty, which is the
    # normal case. Set it only for a doctor who sits at a branch.
    area: Optional[str] = None

    # Defaults to the hospital's setting.
    handles_emergencies: Optional[bool] = None


class DoctorUpdate(BaseModel):
    """Same fields, all optional - for editing a doctor already added."""

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    gender: Optional[str] = Field(default=None, max_length=20)
    phone: Optional[str] = Field(default=None, max_length=20)

    specialty: Optional[str] = None
    qualification: Optional[str] = Field(default=None, max_length=200)
    experience_years: Optional[int] = Field(default=None, ge=0, le=70)
    focus_areas: Optional[str] = Field(default=None, max_length=600)

    consultation_fee: Optional[int] = Field(default=None, ge=0, le=100000)
    languages: Optional[str] = Field(default=None, max_length=200)

    available_days: Optional[str] = Field(default=None, max_length=100)
    next_available: Optional[str] = Field(default=None, max_length=100)

    area: Optional[str] = None
    handles_emergencies: Optional[bool] = None


class HospitalDoctorOut(BaseModel):
    """A doctor as their own hospital sees them - includes the login ID."""

    id: uuid.UUID
    login_id: Optional[str] = None

    full_name: str
    gender: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    specialty: str
    qualification: Optional[str] = None
    experience_years: int = 0
    focus_areas: Optional[str] = None

    hospital: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None

    consultation_fee: Optional[int] = None
    rating: float = 0.0
    reviews_count: int = 0

    languages: Optional[str] = None
    available_days: Optional[str] = None
    next_available: Optional[str] = None
    handles_emergencies: bool = False

    created_at: Optional[datetime] = None

    # True until the doctor has replaced the password they were issued.
    password_pending: bool = True

    class Config:
        from_attributes = True


class DoctorCreated(BaseModel):
    doctor: HospitalDoctorOut
    credentials: IssuedCredentials


class DoctorOptionsOut(BaseModel):
    """Dropdown contents for the add-doctor form.

    Specialties come from the same set the triage step is allowed to
    choose from, and areas from the same map the recommender measures
    distance on. Serving both from the backend is what stops a hospital
    from adding a doctor under a specialty no patient form can ever
    route to.
    """

    specialties: list[str]
    areas: list[str]
    cities: list[str]
    genders: list[str]
    common_languages: list[str]
