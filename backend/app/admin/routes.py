"""
The admin portal.

There is exactly one admin account, created at startup from
ADMIN_EMAIL / ADMIN_PASSWORD (see app/core/bootstrap_admin.py). Its
only job is to bring hospitals onto the platform: fill in the
hospital's details, and hand back an ID and a temporary password for
someone at that hospital to sign in with.

The admin never touches doctors. A hospital adds its own - see
app/hospitals/routes.py.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.hospital import Hospital
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.auth.dependencies import require_role
from app.auth.security import hash_password
from app.auth.credentials import (
    HOSPITAL_PREFIX,
    generate_login_id,
    generate_temporary_password,
)
from app.doctors.locations import AREAS, CITY, area_names, coordinates_for
from app.schemas.admin import (
    AdminStats,
    HospitalCreate,
    HospitalCreated,
    HospitalOut,
    IssuedCredentials,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


# ============================================================
# HELPERS
# ============================================================

def _doctor_counts(db: Session) -> dict:
    rows = (
        db.query(Doctor.hospital_id, func.count(Doctor.id))
        .group_by(Doctor.hospital_id)
        .all()
    )

    return {hospital_id: count for hospital_id, count in rows}


def _to_out(hospital: Hospital, doctor_count: int, password_changed: bool) -> HospitalOut:
    return HospitalOut(
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
        is_active=hospital.is_active,
        created_at=hospital.created_at,
        doctor_count=doctor_count,
        password_changed=password_changed,
    )


# ============================================================
# FORM OPTIONS
# ============================================================

@router.get("/options")
def get_admin_options():
    """Areas the platform knows coordinates for."""

    return {
        "cities": [CITY],
        "areas": area_names(),
        "hospital_types": [
            "Multispeciality",
            "Superspeciality",
            "General",
            "Clinic",
            "Diagnostic Centre",
            "Maternity",
            "Eye Care",
            "Dental",
        ],
    }


# ============================================================
# STATS
# ============================================================

@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db)):
    return AdminStats(
        hospitals=db.query(func.count(Hospital.id)).scalar() or 0,
        doctors=db.query(func.count(Doctor.id)).scalar() or 0,
        patients=db.query(func.count(Patient.id)).scalar() or 0,
        sample_doctors=(
            db.query(func.count(Doctor.id))
            .filter(Doctor.hospital_id.is_(None))
            .scalar()
            or 0
        ),
    )


# ============================================================
# LIST HOSPITALS
# ============================================================

@router.get("/hospitals", response_model=list[HospitalOut])
def list_hospitals(db: Session = Depends(get_db)):
    hospitals = (
        db.query(Hospital)
        .order_by(Hospital.created_at.desc())
        .all()
    )

    counts = _doctor_counts(db)

    # One query for the login state of every hospital account, rather
    # than one per row.
    pending = {
        user_id
        for (user_id,) in db.query(User.id)
        .filter(User.must_change_password.is_(True))
        .all()
    }

    return [
        _to_out(
            hospital,
            counts.get(hospital.id, 0),
            hospital.user_id not in pending,
        )
        for hospital in hospitals
    ]


# ============================================================
# CREATE A HOSPITAL
# ============================================================

@router.post(
    "/hospitals",
    response_model=HospitalCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_hospital(payload: HospitalCreate, db: Session = Depends(get_db)):

    email = payload.email.strip().lower()

    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(
            status_code=400,
            detail="That email already has an account on the platform.",
        )

    if payload.area not in AREAS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pick an area from the list - the recommendation engine "
                "only knows where those are."
            ),
        )

    login_id = generate_login_id(db, HOSPITAL_PREFIX)
    temporary_password = generate_temporary_password()

    user = User(
        email=email,
        hashed_password=hash_password(temporary_password),
        role=UserRole.hospital,
        login_id=login_id,
        must_change_password=True,
        is_active=True,
    )

    db.add(user)
    db.flush()  # need user.id

    point = coordinates_for(payload.area)

    hospital = Hospital(
        user_id=user.id,
        login_id=login_id,
        name=payload.name.strip(),
        registration_number=payload.registration_number,
        hospital_type=payload.hospital_type,
        address=payload.address,
        area=payload.area,
        city=payload.city or CITY,
        pincode=payload.pincode,
        phone=payload.phone,
        email=email,
        contact_person=payload.contact_person,
        contact_phone=payload.contact_phone,
        bed_count=payload.bed_count,
        emergency_services=payload.emergency_services,
    )

    if point:
        hospital.latitude, hospital.longitude = point

    db.add(hospital)
    db.commit()
    db.refresh(hospital)

    return HospitalCreated(
        hospital=_to_out(hospital, 0, password_changed=False),
        credentials=IssuedCredentials(
            login_id=login_id,
            temporary_password=temporary_password,
        ),
    )


# ============================================================
# REISSUE A PASSWORD
# ============================================================
# The temporary password is shown once and never stored in readable
# form, so this is the only way back in for a hospital that lost it.
# The new one is temporary too - they land on the change-password
# screen again.

@router.post("/hospitals/{hospital_id}/reset-password", response_model=IssuedCredentials)
def reset_hospital_password(hospital_id: str, db: Session = Depends(get_db)):

    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()

    if hospital is None:
        raise HTTPException(status_code=404, detail="No such hospital.")

    user = db.query(User).filter(User.id == hospital.user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="This hospital has no login account attached.",
        )

    temporary_password = generate_temporary_password()

    user.hashed_password = hash_password(temporary_password)
    user.must_change_password = True

    db.commit()

    return IssuedCredentials(
        login_id=hospital.login_id,
        temporary_password=temporary_password,
    )


# ============================================================
# DEACTIVATE / REACTIVATE
# ============================================================
# Preferred over deleting: a hospital that has been on the platform has
# doctors, and those doctors may already be attached to patient
# history. Switching it off blocks the logins and hides the doctors
# from recommendations without destroying the trail.

@router.post("/hospitals/{hospital_id}/deactivate", response_model=HospitalOut)
def deactivate_hospital(hospital_id: str, db: Session = Depends(get_db)):
    return _set_hospital_active(hospital_id, False, db)


@router.post("/hospitals/{hospital_id}/activate", response_model=HospitalOut)
def activate_hospital(hospital_id: str, db: Session = Depends(get_db)):
    return _set_hospital_active(hospital_id, True, db)


def _set_hospital_active(hospital_id: str, active: bool, db: Session) -> HospitalOut:

    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()

    if hospital is None:
        raise HTTPException(status_code=404, detail="No such hospital.")

    hospital.is_active = active

    # The hospital's own login, and every doctor login it issued.
    doctor_user_ids = [
        user_id
        for (user_id,) in db.query(Doctor.user_id)
        .filter(Doctor.hospital_id == hospital.id)
        .filter(Doctor.user_id.isnot(None))
        .all()
    ]

    for user_id in [hospital.user_id, *doctor_user_ids]:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = active

    db.commit()
    db.refresh(hospital)

    count = (
        db.query(func.count(Doctor.id))
        .filter(Doctor.hospital_id == hospital.id)
        .scalar()
        or 0
    )

    user = db.query(User).filter(User.id == hospital.user_id).first()

    return _to_out(
        hospital,
        count,
        password_changed=bool(user and not user.must_change_password),
    )


# ============================================================
# DELETE A HOSPITAL
# ============================================================

@router.delete("/hospitals/{hospital_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hospital(hospital_id: str, db: Session = Depends(get_db)):
    """Remove a hospital, its doctors, and all of their logins.

    Only reach for this on a hospital that was added by mistake. Use
    deactivate for one that has actually been in use.
    """

    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()

    if hospital is None:
        raise HTTPException(status_code=404, detail="No such hospital.")

    doctors = (
        db.query(Doctor)
        .filter(Doctor.hospital_id == hospital.id)
        .all()
    )

    doctor_user_ids = [doctor.user_id for doctor in doctors if doctor.user_id]

    for doctor in doctors:
        db.delete(doctor)

    db.flush()

    for user_id in doctor_user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)

    hospital_user_id = hospital.user_id

    db.delete(hospital)
    db.flush()

    hospital_user = db.query(User).filter(User.id == hospital_user_id).first()

    if hospital_user:
        db.delete(hospital_user)

    db.commit()

    return None
