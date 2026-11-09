"""
The doctor's half of the doctor-access flow.

Separate from app/doctors/routes.py (the patient-facing directory and
recommendation engine) and app/doctors/portal.py (a doctor's own
profile) - this is the third thing a logged-in doctor can do: look a
patient up by Health ID, ask them for access, and once they say yes,
read that one patient's record and ask the same kind of question about
them that the patient can ask about themselves.

Every read below is gated on an APPROVED row in access_requests for
this exact (doctor, patient) pair - see _active_access(). A pending,
denied or revoked request grants nothing.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.report import Report
from app.models.access_request import AccessRequest, AccessStatus
from app.core.ledger import record_event
from app.core.ledger_hash import EventType
from app.models.doctor_chat_message import DoctorChatMessage
from app.auth.dependencies import get_current_doctor
from app.schemas.access import (
    AccessRequestCreate,
    AccessRequestOut,
    PatientBrief,
    PatientLookupOut,
    PatientRecordOut,
    DoctorChatRequest,
    DoctorChatResponse,
    DoctorChatHistoryOut,
)
from app.schemas.report import ReportOut
from app.reports import summary_service
from app.chat.routes import _get_pipeline, HISTORY_TURNS

router = APIRouter(prefix="/doctor", tags=["doctor-patient-access"])


# ============================================================
# HELPERS
# ============================================================

def _normalized_health_id(raw: str) -> str:
    """Strip the spaces a person typing "9214 7736 0025" would include."""
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _find_patient_by_health_id(health_id: str, db: Session) -> Patient:
    cleaned = _normalized_health_id(health_id)

    patient = (
        db.query(Patient).filter(Patient.health_id == cleaned).first()
        if cleaned
        else None
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No patient found with that Health ID. Check the "
                "number and try again."
            ),
        )

    return patient


def _open_request(doctor: Doctor, patient: Patient, db: Session) -> AccessRequest | None:
    """The pending or approved row for this pair, if there is one."""

    return (
        db.query(AccessRequest)
        .filter(AccessRequest.doctor_id == doctor.id)
        .filter(AccessRequest.patient_id == patient.id)
        .filter(
            AccessRequest.status.in_(
                [AccessStatus.PENDING, AccessStatus.APPROVED]
            )
        )
        .order_by(AccessRequest.created_at.desc())
        .first()
    )


def _active_access(doctor: Doctor, patient_id: str, db: Session) -> AccessRequest:
    """An APPROVED row for this doctor and patient, or a 403.

    Every endpoint that reads patient data below depends on this - a
    doctor cannot read a record just by knowing the Health ID, only
    after the patient has approved the request.
    """

    access = (
        db.query(AccessRequest)
        .filter(AccessRequest.doctor_id == doctor.id)
        .filter(AccessRequest.patient_id == patient_id)
        .filter(AccessRequest.status == AccessStatus.APPROVED)
        .order_by(AccessRequest.decided_at.desc())
        .first()
    )

    if access is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have approved access to this patient's "
                "record. Send an access request from Find patient."
            ),
        )

    return access


# ============================================================
# FIND PATIENT (by Health ID)
# ============================================================

@router.get("/patients/lookup", response_model=PatientLookupOut)
def lookup_patient(
    health_id: str,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """Confirms whose record a request is about to go to, and shows
    whether one already exists - so the button on Find patient reads
    "Send request", "Request pending" or "You already have access"
    instead of letting a doctor fire off a duplicate."""

    patient = _find_patient_by_health_id(health_id, db)
    existing = _open_request(doctor, patient, db)

    return PatientLookupOut(
        id=patient.id,
        health_id=patient.health_id,
        full_name=patient.full_name,
        age=patient.age,
        gender=patient.gender,
        access_status=existing.status if existing else None,
    )


# ============================================================
# SEND AN ACCESS REQUEST
# ============================================================

@router.post("/access-requests", response_model=AccessRequestOut, status_code=201)
def send_access_request(
    payload: AccessRequestCreate,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    patient = _find_patient_by_health_id(payload.health_id, db)

    existing = _open_request(doctor, patient, db)

    if existing is not None:
        detail = (
            "You already have access to this patient's record."
            if existing.status == AccessStatus.APPROVED
            else "You already have a pending request for this patient."
        )
        raise HTTPException(status_code=400, detail=detail)

    request = AccessRequest(
        doctor_id=doctor.id,
        patient_id=patient.id,
        note=(payload.note or "").strip() or None,
        status=AccessStatus.PENDING,
    )

    db.add(request)

    # flush() assigns request.id without committing, which the ledger
    # event needs. The commit below then saves request + event together.
    db.flush()
    record_event(db, request, EventType.REQUESTED)

    db.commit()
    db.refresh(request)

    return request


# ============================================================
# MY PATIENTS (approved access only)
# ============================================================

@router.get("/patients", response_model=list[AccessRequestOut])
def list_my_patients(
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return (
        db.query(AccessRequest)
        .filter(AccessRequest.doctor_id == doctor.id)
        .filter(AccessRequest.status == AccessStatus.APPROVED)
        .order_by(AccessRequest.decided_at.desc())
        .all()
    )


# ============================================================
# READ ONE PATIENT'S RECORD
# ============================================================

@router.get("/patients/{patient_id}/record", response_model=PatientRecordOut)
def get_patient_record(
    patient_id: str,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    access = _active_access(doctor, patient_id, db)

    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # Same cached summary the patient's own dashboard reads - a doctor
    # never triggers a fresh model call just by opening the record.
    cached_summary = summary_service.get_cached_summary(patient, db)

    reports = (
        db.query(Report)
        .filter(Report.patient_id == patient.id)
        .order_by(Report.uploaded_at.desc())
        .all()
    )

    return PatientRecordOut(
        patient=PatientBrief.model_validate(patient),
        access=AccessRequestOut.model_validate(access),
        clinical_summary=cached_summary["summary"]
        or "No processed reports yet for this patient.",
        observation_count=cached_summary["observation_count"],
        reports_analyzed=cached_summary["reports_analyzed"],
        summary_generated_at=cached_summary["generated_at"],
        reports=[ReportOut.model_validate(report) for report in reports],
    )


# ============================================================
# "ASK ABOUT THIS PATIENT"
# ============================================================

def _load_recent_doctor_history(
    doctor: Doctor, patient_id: str, db: Session, limit: int
) -> list[DoctorChatMessage]:
    rows = (
        db.query(DoctorChatMessage)
        .filter(DoctorChatMessage.doctor_id == doctor.id)
        .filter(DoctorChatMessage.patient_id == patient_id)
        .order_by(DoctorChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


@router.get(
    "/patients/{patient_id}/chat/history",
    response_model=DoctorChatHistoryOut,
)
def get_patient_chat_history(
    patient_id: str,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    _active_access(doctor, patient_id, db)

    rows = (
        db.query(DoctorChatMessage)
        .filter(DoctorChatMessage.doctor_id == doctor.id)
        .filter(DoctorChatMessage.patient_id == patient_id)
        .order_by(DoctorChatMessage.created_at.asc())
        .all()
    )

    return DoctorChatHistoryOut(messages=rows)


@router.post(
    "/patients/{patient_id}/chat",
    response_model=DoctorChatResponse,
)
def ask_about_patient(
    patient_id: str,
    payload: DoctorChatRequest,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    _active_access(doctor, patient_id, db)

    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")

    message = payload.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Only this patient's own analyzed reports - same rule the
    # patient's own chatbot follows in app/chat/routes.py.
    own_document_ids = [
        str(report_id)
        for (report_id,) in db.query(Report.id)
        .filter(Report.patient_id == patient.id, Report.analyzed.is_(True))
        .all()
    ]

    retriever, router_, context_builder, generator = _get_pipeline()

    route = router_.route(message)
    comprehensive = route["scope"] == "comprehensive"

    retrieval_result = retriever.retrieve(
        message,
        comprehensive=comprehensive,
        document_ids=own_document_ids,
    )

    observations = retrieval_result["patient"]["observations"]
    knowledge = retrieval_result["knowledge"]

    persisted = _load_recent_doctor_history(doctor, patient.id, db, HISTORY_TURNS)
    turn_lines = [
        f"{'User' if row.role == 'user' else 'Assistant'}: {row.content}"
        for row in persisted
    ]
    conversation_history = "\n".join(turn_lines)

    # Anchor with the patient's cached overall health summary, the
    # same way the patient's own chat does, and make clear to the
    # model that it is answering a doctor about someone else's
    # records, not the patient themself.
    cached_summary = summary_service.get_cached_summary(patient, db)
    if cached_summary.get("reports_analyzed", 0) > 0:
        conversation_history = (
            f"[This patient's overall health summary on file]\n"
            f"{cached_summary['summary']}\n\n{conversation_history}"
        ).strip()

    context = context_builder.build(query=message, retrieval_result=retrieval_result)
    answer = generator.generate(
        query=message,
        retrieved_context=context,
        conversation_history=conversation_history,
    )

    db.add(
        DoctorChatMessage(
            doctor_id=doctor.id,
            patient_id=patient.id,
            role="user",
            content=message,
        )
    )
    db.add(
        DoctorChatMessage(
            doctor_id=doctor.id,
            patient_id=patient.id,
            role="assistant",
            content=answer,
        )
    )
    db.commit()

    return DoctorChatResponse(
        answer=answer,
        scope=route["scope"],
        patient_observations_used=len(observations),
        knowledge_chunks_used=len(knowledge),
    )
