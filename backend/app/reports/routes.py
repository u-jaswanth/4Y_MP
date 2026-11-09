import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import REPORTS_UPLOAD_DIR
from app.core.cloudinary_client import upload_file
from app.models.patient import Patient
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportOut, HealthSummaryOut, TrendsOut
from app.auth.dependencies import get_current_patient
from app.auth.security import decode_access_token
from app.ingestion_pipeline import ingest_report
from app.reports import summary_service, report_summary_service, trend_service

router = APIRouter(prefix="/reports", tags=["reports"])

os.makedirs(REPORTS_UPLOAD_DIR, exist_ok=True)


# ============================================================
# SHARED PROCESSING STEP
# ============================================================
#
# Everything that used to sit behind the "Analyze" button now lives
# here and runs as part of upload:
#
#   1. index the report so it's searchable (ingest_report)
#   2. write this report's own plain-language summary
#   3. refold every processed report into the overall health summary
#      that the dashboard and the Reports header card read
#
# It never raises. A failure is recorded on the report row and surfaced
# through `status` / `error_message`, so the upload itself still
# succeeds and the file is never lost.

def _process_report(report: Report, patient: Patient, db: Session) -> Report:

    # --- 1. index -------------------------------------------------
    try:
        ingest_report(report.file_path, str(report.id))

        report.analyzed = True
        report.analysis_error = None
        report.analyzed_at = datetime.utcnow()

    except Exception as error:  # noqa: BLE001
        report.analyzed = False
        report.analysis_error = str(error)

    db.add(report)
    db.commit()
    db.refresh(report)

    if not report.analyzed:
        return report

    # --- 2. this report's own summary -----------------------------
    report = report_summary_service.regenerate_and_store(report, db)

    # --- 3. the combined, cross-report summary --------------------
    try:
        summary_service.regenerate_and_store_summary(patient, db)
    except Exception:  # noqa: BLE001 - never fail the request over this
        pass

    db.refresh(report)

    return report


# ============================================================
# UPLOAD A REPORT
# ============================================================
#
# NOTE ON TIMING: processing runs inline, so the response already
# carries `ai_summary` and the frontend can render the explanation the
# moment the upload finishes - no polling, no second click. The cost is
# a slower upload request (OCR + model call). If that ever becomes a
# problem, move the `_process_report` call into a FastAPI
# BackgroundTask and have the Reports page poll GET /reports/ until
# `status` leaves "processing"; nothing else has to change.

@router.post("/upload", response_model=ReportOut)
async def upload_report(
    file: UploadFile = File(...),
    report_name: Optional[str] = Form(None),
    report_type: Optional[str] = Form(None),
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF reports are supported")

    stored_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(REPORTS_UPLOAD_DIR, stored_filename)

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    # Local file_path above is what the ingestion pipeline reads from
    # and always exists. Cloudinary is an optional, best-effort mirror
    # (see app/core/cloudinary_client.py) - if it's not configured or
    # the upload fails, cloud_url/cloud_public_id just stay None.
    cloud_result = upload_file(
        contents,
        folder=f"mediconnect/reports/{current_patient.id}",
    )

    report = Report(
        patient_id=current_patient.id,
        filename=file.filename,
        report_name=(report_name or file.filename or "").strip() or file.filename,
        report_type=(report_type or "other").strip().lower(),
        file_path=file_path,
        cloud_url=cloud_result["secure_url"] if cloud_result else None,
        cloud_public_id=cloud_result["public_id"] if cloud_result else None,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return _process_report(report, current_patient, db)


# ============================================================
# SERVE THE RAW PDF (used by the "View" button)
# ============================================================
#
# NOTE ON AUTH: this is opened as a plain link (<a target="_blank">
# or window.open), not fetched with `fetch()`, so the browser will
# NOT attach the normal `Authorization: Bearer <token>` header.
# To keep the file access authenticated we also accept the token as a
# query param here; the frontend appends it when it doesn't have a
# Cloudinary URL to use instead.

def _patient_from_token(token: Optional[str], db: Session) -> Optional[Patient]:
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None

    return db.query(Patient).filter(Patient.user_id == user.id).first()


def _doctor_from_token(token: Optional[str], db: Session):
    """Same idea as _patient_from_token, for a doctor viewing a
    patient's report through the doctor-access flow (see
    app/doctors/patient_access.py). Imported lazily to avoid a circular
    import at module load time (app.models.doctor <-> app.database is
    fine, but app.doctors.patient_access imports app.chat.routes,
    which is heavier than this file needs on every request)."""

    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    from app.models.doctor import Doctor

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None

    return db.query(Doctor).filter(Doctor.user_id == user.id).first()


@router.get("/{report_id}/file")
def get_report_file(
    report_id: uuid.UUID,
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    patient = _patient_from_token(token, db)

    if patient is not None:
        report = (
            db.query(Report)
            .filter(Report.id == report_id, Report.patient_id == patient.id)
            .first()
        )

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

    else:
        # Not a patient's own token - maybe a doctor with approved
        # access to the patient this report belongs to.
        from app.models.access_request import AccessRequest, AccessStatus

        doctor = _doctor_from_token(token, db)

        if doctor is None:
            raise HTTPException(status_code=401, detail="Not authenticated")

        report = db.query(Report).filter(Report.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        has_access = (
            db.query(AccessRequest)
            .filter(AccessRequest.doctor_id == doctor.id)
            .filter(AccessRequest.patient_id == report.patient_id)
            .filter(AccessRequest.status == AccessStatus.APPROVED)
            .first()
        )

        if has_access is None:
            raise HTTPException(
                status_code=403,
                detail="You do not have approved access to this patient's record.",
            )

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file is missing on disk")

    return FileResponse(
        report.file_path,
        media_type="application/pdf",
        filename=report.filename or "report.pdf",
    )


# ============================================================
# LIST REPORTS FOR THE CURRENT PATIENT
# ============================================================

@router.get("/", response_model=list[ReportOut])
def list_reports(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    return (
        db.query(Report)
        .filter(Report.patient_id == current_patient.id)
        .order_by(Report.uploaded_at.desc())
        .all()
    )


# ============================================================
# RE-SUMMARIZE ONE REPORT
# ============================================================
#
# Replaces the old POST /{report_id}/analyze. Upload already does this
# work; this endpoint exists so the user can retry a report whose first
# pass failed, or regenerate an explanation on demand.

@router.post("/{report_id}/summarize", response_model=ReportOut)
def summarize_report(
    report_id: uuid.UUID,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.patient_id == current_patient.id)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Already indexed: only the explanation needs rebuilding, which
    # skips OCR entirely and comes back in a couple of seconds.
    if report.analyzed:
        report = report_summary_service.regenerate_and_store(report, db)

        try:
            summary_service.regenerate_and_store_summary(current_patient, db)
        except Exception:  # noqa: BLE001
            pass

        db.refresh(report)
        return report

    # Never indexed, or a previous attempt failed - run the full pass.
    return _process_report(report, current_patient, db)


# ============================================================
# OVERALL HEALTH SUMMARY (reads the cached summary - no model
# call on the common path; see app/reports/summary_service.py)
# ============================================================

@router.get("/summary", response_model=HealthSummaryOut)
def get_health_summary(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    payload = summary_service.get_cached_summary(current_patient, db)
    return HealthSummaryOut(**payload)


# ============================================================
# LAB VALUE TRENDS (read-only - see app/reports/trend_service.py)
# ============================================================

@router.get("/trends", response_model=TrendsOut)
def get_trends(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    return TrendsOut(**trend_service.build_trends(current_patient, db))
