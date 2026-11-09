"""
The doctor portal.

Small on purpose. A doctor does not sign themselves up and does not own
their own record - their hospital added them, and their hospital
maintains them. So all this exposes is the profile as it stands,
which is also exactly what a patient sees on a recommendation card.

Separate from app/doctors/routes.py, which is the patient-facing
directory and recommendation engine, so that "what patients can look
up" and "what a logged-in doctor can see about themselves" never share
a code path by accident.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.models.hospital import Hospital
from app.auth.dependencies import get_current_doctor
from app.schemas.doctor import DoctorSelfOut

router = APIRouter(prefix="/doctor", tags=["doctor"])


@router.get("/profile", response_model=DoctorSelfOut)
def get_my_profile(
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    hospital_phone = None

    if doctor.hospital_id:
        hospital = (
            db.query(Hospital)
            .filter(Hospital.id == doctor.hospital_id)
            .first()
        )

        if hospital:
            hospital_phone = hospital.phone

    return DoctorSelfOut(
        id=doctor.id,
        login_id=doctor.login_id,
        full_name=doctor.full_name,
        gender=doctor.gender,
        email=doctor.email,
        phone=doctor.phone,
        specialty=doctor.specialty,
        qualification=doctor.qualification,
        experience_years=doctor.experience_years or 0,
        focus_list=doctor.focus_list,
        language_list=doctor.language_list,
        hospital=doctor.hospital,
        hospital_phone=hospital_phone,
        area=doctor.area,
        city=doctor.city,
        consultation_fee=doctor.consultation_fee,
        rating=doctor.rating or 0.0,
        reviews_count=doctor.reviews_count or 0,
        available_days=doctor.available_days,
        next_available=doctor.next_available,
        handles_emergencies=bool(doctor.handles_emergencies),
        created_at=doctor.created_at,
    )
