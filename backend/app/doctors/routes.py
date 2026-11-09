from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.auth.dependencies import get_current_patient
from app.schemas.doctor import (
    DoctorOut,
    RecommendationRequest,
    RecommendationOut,
    OptionsOut,
)
from app.doctors import triage as triage_service
from app.doctors import recommender
from app.doctors.locations import CITY, area_names

router = APIRouter(prefix="/doctors", tags=["doctors"])


# ============================================================
# FORM OPTIONS
# ============================================================
# The dropdowns are served from the same module that does the routing,
# so the options a user can pick and the specialties they map to can
# never drift apart.

@router.get("/options", response_model=OptionsOut)
def get_options():
    return OptionsOut(
        concerns=triage_service.HEALTH_CONCERNS,
        durations=triage_service.DURATIONS,
        severities=triage_service.SEVERITIES,
        cities=[CITY],
        areas=area_names(),
    )


# ============================================================
# THE WHOLE DIRECTORY
# ============================================================

@router.get("/", response_model=list[DoctorOut])
def list_doctors(
    specialty: str | None = None,
    area: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Doctor)

    if specialty:
        query = query.filter(Doctor.specialty == specialty)

    if area:
        query = query.filter(Doctor.area == area)

    return query.order_by(Doctor.rating.desc()).all()


# ============================================================
# RECOMMEND
# ============================================================

@router.post("/recommend", response_model=RecommendationOut)
def recommend_doctors(
    payload: RecommendationRequest,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    form = payload.model_dump()

    # The patient's own cached report summary is handed to the triage
    # step as background, so a case like "tired for weeks" is read
    # against their actual results rather than in a vacuum. It is never
    # shown back to them here - the Reports page owns that.
    result = triage_service.understand_case(
        form,
        report_summary=current_patient.ai_summary,
    )

    matches = recommender.rank_doctors(db, result, form)

    return RecommendationOut(
        case_summary=result["case_summary"],
        specialties=result["specialties"],
        urgency=result["urgency"],
        red_flags=result["red_flags"],
        questions_for_doctor=result["questions_for_doctor"],
        before_the_visit=result["before_the_visit"],
        ai_reading_used=result["ai_reading_used"],
        matches=matches,
    )
