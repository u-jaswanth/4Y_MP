"""
The hospital portal.

A hospital cannot sign itself up - an admin issues the account (see
app/admin/routes.py). Once in, the hospital manages its own doctors:
add one, hand them the ID and temporary password that comes back, and
remove them when they leave.

Every query in here is scoped by `Doctor.hospital_id == hospital.id`.
A hospital can only ever see and change the doctors it added; the
seeded sample doctors have a NULL hospital_id and so belong to nobody.
"""

import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import REPORTS_UPLOAD_DIR
from app.core.cloudinary_client import upload_file
from app.models.user import User, UserRole
from app.models.hospital import Hospital
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.report import Report
from app.auth.dependencies import get_current_hospital
from app.auth.security import hash_password
from app.auth.credentials import (
    DOCTOR_PREFIX,
    generate_doctor_slug,
    generate_login_id,
    generate_temporary_password,
)
from app.doctors.locations import AREAS, CITY, area_names, coordinates_for
from app.doctors.triage import KNOWN_SPECIALTIES
from app.schemas.admin import IssuedCredentials
from app.schemas.hospital import (
    DoctorCreate,
    DoctorCreated,
    DoctorOptionsOut,
    DoctorUpdate,
    HospitalDoctorOut,
    HospitalProfileOut,
    HospitalReportOut,
    PatientLookupOut,
)
from app.schemas.report import ReportOut

# Imported rather than duplicated - this already does everything an
# upload needs done to it (index it, write its summary, refold the
# patient's combined health summary) and must never drift from the
# patient's own upload path in app/reports/routes.py.
from app.reports.routes import _process_report

router = APIRouter(prefix="/hospital", tags=["hospital"])

os.makedirs(REPORTS_UPLOAD_DIR, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def _to_out(doctor: Doctor, password_pending: bool) -> HospitalDoctorOut:
    return HospitalDoctorOut(
        id=doctor.id,
        login_id=doctor.login_id,
        full_name=doctor.full_name,
        gender=doctor.gender,
        email=doctor.email,
        phone=doctor.phone,
        specialty=doctor.specialty,
        qualification=doctor.qualification,
        experience_years=doctor.experience_years or 0,
        focus_areas=doctor.focus_areas,
        hospital=doctor.hospital,
        area=doctor.area,
        city=doctor.city,
        consultation_fee=doctor.consultation_fee,
        rating=doctor.rating or 0.0,
        reviews_count=doctor.reviews_count or 0,
        languages=doctor.languages,
        available_days=doctor.available_days,
        next_available=doctor.next_available,
        handles_emergencies=bool(doctor.handles_emergencies),
        created_at=doctor.created_at,
        password_pending=password_pending,
    )


def _pending_user_ids(db: Session, doctors: list[Doctor]) -> set:
    """Which of these doctors have not changed their issued password yet."""

    user_ids = [doctor.user_id for doctor in doctors if doctor.user_id]

    if not user_ids:
        return set()

    return {
        user_id
        for (user_id,) in db.query(User.id)
        .filter(User.id.in_(user_ids))
        .filter(User.must_change_password.is_(True))
        .all()
    }


def _owned_doctor(doctor_id: str, hospital: Hospital, db: Session) -> Doctor:
    doctor = (
        db.query(Doctor)
        .filter(Doctor.id == doctor_id)
        .filter(Doctor.hospital_id == hospital.id)
        .first()
    )

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="No such doctor at this hospital.",
        )

    return doctor


# ============================================================
# FORM OPTIONS
# ============================================================

@router.get("/options", response_model=DoctorOptionsOut)
def get_doctor_form_options(
    hospital: Hospital = Depends(get_current_hospital),
):
    return DoctorOptionsOut(
        specialties=sorted(KNOWN_SPECIALTIES),
        areas=area_names(),
        cities=[CITY],
        genders=["Female", "Male", "Other"],
        common_languages=[
            "Telugu",
            "Hindi",
            "English",
            "Urdu",
            "Tamil",
            "Kannada",
            "Marathi",
        ],
    )


# ============================================================
# PROFILE
# ============================================================

@router.get("/profile", response_model=HospitalProfileOut)
def get_hospital_profile(
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    count = (
        db.query(func.count(Doctor.id))
        .filter(Doctor.hospital_id == hospital.id)
        .scalar()
        or 0
    )

    return HospitalProfileOut(
        id=hospital.id,
        login_id=hospital.login_id,
        name=hospital.name,
        registration_number=hospital.registration_number,
        hospital_type=hospital.hospital_type,
        address=hospital.address,
        area=hospital.area,
        city=hospital.city,
        pincode=hospital.pincode,
        phone=hospital.phone,
        email=hospital.email,
        contact_person=hospital.contact_person,
        contact_phone=hospital.contact_phone,
        bed_count=hospital.bed_count,
        emergency_services=hospital.emergency_services,
        created_at=hospital.created_at,
        doctor_count=count,
    )


# ============================================================
# LIST DOCTORS
# ============================================================

@router.get("/doctors", response_model=list[HospitalDoctorOut])
def list_hospital_doctors(
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    doctors = (
        db.query(Doctor)
        .filter(Doctor.hospital_id == hospital.id)
        .order_by(Doctor.full_name)
        .all()
    )

    pending = _pending_user_ids(db, doctors)

    return [_to_out(doctor, doctor.user_id in pending) for doctor in doctors]


# ============================================================
# ADD A DOCTOR
# ============================================================

@router.post(
    "/doctors",
    response_model=DoctorCreated,
    status_code=status.HTTP_201_CREATED,
)
def add_doctor(
    payload: DoctorCreate,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()

    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(
            status_code=400,
            detail="That email already has an account on the platform.",
        )

    if payload.specialty not in KNOWN_SPECIALTIES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pick a specialty from the list. Patient symptom forms "
                "can only route to those, so a doctor filed under "
                "anything else would never be recommended."
            ),
        )

    # Normally the hospital's own area; set per-doctor only for a branch.
    area = (payload.area or hospital.area or "").strip()

    if area not in AREAS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pick an area from the list - it is what the "
                "recommendation engine measures distance from."
            ),
        )

    login_id = generate_login_id(db, DOCTOR_PREFIX)
    temporary_password = generate_temporary_password()

    user = User(
        email=email,
        hashed_password=hash_password(temporary_password),
        role=UserRole.doctor,
        login_id=login_id,
        must_change_password=True,
        is_active=True,
    )

    db.add(user)
    db.flush()

    point = coordinates_for(area)

    doctor = Doctor(
        slug=generate_doctor_slug(db, payload.full_name),
        hospital_id=hospital.id,
        user_id=user.id,
        login_id=login_id,
        email=email,
        phone=payload.phone,
        full_name=payload.full_name.strip(),
        gender=payload.gender,
        specialty=payload.specialty,
        qualification=payload.qualification,
        experience_years=payload.experience_years or 0,
        focus_areas=payload.focus_areas,
        # The hospital's own name and location travel with the doctor,
        # so the recommendation card reads the same way as it does for
        # the seeded rows.
        hospital=hospital.name,
        area=area,
        city=hospital.city or CITY,
        latitude=point[0] if point else None,
        longitude=point[1] if point else None,
        consultation_fee=payload.consultation_fee,
        languages=payload.languages,
        available_days=payload.available_days,
        next_available=payload.next_available,
        handles_emergencies=(
            hospital.emergency_services
            if payload.handles_emergencies is None
            else payload.handles_emergencies
        ),
        # Earned from patient feedback later, never typed in here.
        rating=0.0,
        reviews_count=0,
    )

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    return DoctorCreated(
        doctor=_to_out(doctor, password_pending=True),
        credentials=IssuedCredentials(
            login_id=login_id,
            temporary_password=temporary_password,
        ),
    )


# ============================================================
# EDIT A DOCTOR
# ============================================================

@router.patch("/doctors/{doctor_id}", response_model=HospitalDoctorOut)
def update_doctor(
    doctor_id: str,
    payload: DoctorUpdate,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    doctor = _owned_doctor(doctor_id, hospital, db)

    changes = payload.model_dump(exclude_unset=True)

    if "specialty" in changes and changes["specialty"] not in KNOWN_SPECIALTIES:
        raise HTTPException(
            status_code=400,
            detail="Pick a specialty from the list.",
        )

    if "area" in changes and changes["area"]:
        if changes["area"] not in AREAS:
            raise HTTPException(
                status_code=400,
                detail="Pick an area from the list.",
            )

        point = coordinates_for(changes["area"])

        # Coordinates are derived, never sent by the client - so they
        # cannot drift away from the area they are supposed to match.
        doctor.latitude = point[0] if point else None
        doctor.longitude = point[1] if point else None

    for field, value in changes.items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)

    pending = _pending_user_ids(db, [doctor])

    return _to_out(doctor, doctor.user_id in pending)


# ============================================================
# REISSUE A DOCTOR'S PASSWORD
# ============================================================

@router.post(
    "/doctors/{doctor_id}/reset-password",
    response_model=IssuedCredentials,
)
def reset_doctor_password(
    doctor_id: str,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    doctor = _owned_doctor(doctor_id, hospital, db)

    user = db.query(User).filter(User.id == doctor.user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="This doctor has no login account attached.",
        )

    temporary_password = generate_temporary_password()

    user.hashed_password = hash_password(temporary_password)
    user.must_change_password = True

    db.commit()

    return IssuedCredentials(
        login_id=doctor.login_id,
        temporary_password=temporary_password,
    )


# ============================================================
# REMOVE A DOCTOR
# ============================================================

@router.delete("/doctors/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(
    doctor_id: str,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    """Remove a doctor from this hospital, and delete their login.

    They stop appearing in patient recommendations immediately, because
    the recommender reads this table directly.
    """

    doctor = _owned_doctor(doctor_id, hospital, db)

    user_id = doctor.user_id

    db.delete(doctor)
    db.flush()

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            db.delete(user)

    db.commit()

    return None


# ============================================================
# UPLOAD A REPORT TO A PATIENT'S ACCOUNT (by Health ID)
# ============================================================
#
# The one thing a hospital can do that touches a patient it did not
# create: front-desk or lab staff enter the Health ID printed on the
# patient's card (or on their dashboard) and attach a report straight
# to that patient's own account, the same way the patient's own
# upload does it. There is no separate staff login - the person's name
# is recorded on the report itself for the audit trail, the way the
# mock-up's "Recorded by" field does it.
#
# A hospital can reach ANY patient this way, not just ones it has some
# prior relationship with - a Health ID is meant to work at any
# hospital, the same way a physical ID card would. It can only ever
# add a report, never read the patient's existing ones back.

def _normalized_health_id(raw: str) -> str:
    """Strip the spaces a person typing "9214 7736 0025" would include."""
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _find_patient_by_health_id(health_id: str, db: Session) -> Patient:
    cleaned = _normalized_health_id(health_id)

    patient = (
        db.query(Patient)
        .filter(Patient.health_id == cleaned)
        .first()
        if cleaned
        else None
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No patient found with that Health ID. Check the "
                "number on their card or dashboard and try again."
            ),
        )

    return patient


@router.get("/patients/lookup", response_model=PatientLookupOut)
def lookup_patient(
    health_id: str,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    """Confirm whose account an upload is about to go to.

    Called as the person finishes typing the ID, before the file
    picker even opens, so staff see a name to check against the person
    in front of them rather than uploading blind.
    """

    patient = _find_patient_by_health_id(health_id, db)

    return PatientLookupOut(
        health_id=patient.health_id,
        full_name=patient.full_name,
        age=patient.age,
        gender=patient.gender,
    )


@router.post(
    "/patients/{health_id}/reports",
    response_model=HospitalReportOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_report_for_patient(
    health_id: str,
    file: UploadFile = File(...),
    report_name: str | None = Form(None),
    report_type: str | None = Form(None),
    staff_name: str | None = Form(None),
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    patient = _find_patient_by_health_id(health_id, db)

    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF reports are supported")

    stored_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(REPORTS_UPLOAD_DIR, stored_filename)

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    cloud_result = upload_file(
        contents,
        folder=f"mediconnect/reports/{patient.id}",
    )

    report = Report(
        patient_id=patient.id,
        filename=file.filename,
        report_name=(report_name or file.filename or "").strip() or file.filename,
        report_type=(report_type or "other").strip().lower(),
        file_path=file_path,
        cloud_url=cloud_result["secure_url"] if cloud_result else None,
        cloud_public_id=cloud_result["public_id"] if cloud_result else None,
        uploaded_by_hospital=hospital.name,
        uploaded_by_staff=(staff_name or "").strip() or None,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    report = _process_report(report, patient, db)

    return HospitalReportOut(
        **ReportOut.model_validate(report).model_dump(),
        patient_health_id=patient.health_id,
        patient_full_name=patient.full_name,
    )
