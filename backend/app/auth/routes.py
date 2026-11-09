import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import AADHAAR_UPLOAD_DIR
from app.core.cloudinary_client import upload_file
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.hospital import Hospital
from app.models.doctor import Doctor
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserOut,
    AccountOut,
    PatientOut,
    PasswordChange,
)
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.credentials import password_problem, generate_health_id
from app.auth.dependencies import get_current_user, get_current_patient

router = APIRouter(prefix="/auth", tags=["auth"])

os.makedirs(AADHAAR_UPLOAD_DIR, exist_ok=True)


# ============================================================
# DISPLAY NAME
# ============================================================

def display_name_for(user: User, db: Session) -> str | None:
    """What to greet this account as, whichever portal they land in."""

    if user.role == UserRole.patient:
        patient = (
            db.query(Patient)
            .filter(Patient.user_id == user.id)
            .first()
        )
        return patient.full_name if patient else None

    if user.role == UserRole.hospital:
        hospital = (
            db.query(Hospital)
            .filter(Hospital.user_id == user.id)
            .first()
        )
        return hospital.name if hospital else None

    if user.role == UserRole.doctor:
        doctor = (
            db.query(Doctor)
            .filter(Doctor.user_id == user.id)
            .first()
        )
        return doctor.full_name if doctor else None

    return "Administrator"


# ============================================================
# GENERIC USER REGISTRATION
# ============================================================
# Left in place for local development only. Hospital and doctor
# accounts are NOT created here - a hospital is issued by the admin
# (POST /admin/hospitals) and a doctor by their hospital (POST
# /hospital/doctors), because both need a profile row and a generated
# login ID alongside the users row. Anything created through this
# endpoint with role=hospital or role=doctor would have neither, and
# would fail at the portal with "no profile found".

@router.post("/register", response_model=UserOut)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    if role in {UserRole.hospital, UserRole.doctor}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Hospital accounts are issued by an administrator and "
                "doctor accounts by their hospital."
            ),
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ============================================================
# PATIENT REGISTRATION (multipart form, incl. Aadhaar photo)
# ============================================================

@router.post("/register/patient", response_model=UserOut)
def register_patient(
    full_name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    aadhaar_number: str = Form(...),
    aadhaar_consent: bool = Form(...),
    aadhaar_photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if not aadhaar_consent:
        raise HTTPException(
            status_code=400,
            detail="Aadhaar consent is required to register",
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=UserRole.patient,
    )

    db.add(user)
    db.flush()  # get user.id before commit

    file_ext = os.path.splitext(aadhaar_photo.filename or "")[1] or ".jpg"
    aadhaar_filename = f"{uuid.uuid4()}{file_ext}"
    aadhaar_path = os.path.join(AADHAAR_UPLOAD_DIR, aadhaar_filename)

    aadhaar_bytes = aadhaar_photo.file.read()

    with open(aadhaar_path, "wb") as f:
        f.write(aadhaar_bytes)

    # Local aadhaar_path is the source of truth. Cloudinary is an
    # optional, best-effort mirror - see app/core/cloudinary_client.py.
    cloud_result = upload_file(
        aadhaar_bytes,
        folder=f"mediconnect/aadhaar/{user.id}",
    )

    patient = Patient(
        user_id=user.id,
        full_name=full_name,
        age=age,
        gender=gender,
        mobile=mobile,
        health_id=generate_health_id(db),
        aadhaar_number=aadhaar_number,
        aadhaar_photo_path=aadhaar_path,
        aadhaar_consent=aadhaar_consent,
        aadhaar_photo_url=cloud_result["secure_url"] if cloud_result else None,
        aadhaar_photo_public_id=cloud_result["public_id"] if cloud_result else None,
    )

    db.add(patient)
    db.commit()
    db.refresh(user)

    return user


# ============================================================
# LOGIN
# ============================================================

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    principal = payload.principal

    # Patients type an email, hospitals and doctors type the ID they
    # were issued. Both are matched case-insensitively, so HOSP-K7M2Q4
    # and hosp-k7m2q4 are the same account.
    user = (
        db.query(User)
        .filter(
            (func.lower(User.email) == principal.lower())
            | (func.upper(User.login_id) == principal.upper())
        )
        .first()
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That ID or password is not right.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        role=user.role.value,
        must_change_password=user.must_change_password,
        display_name=display_name_for(user, db),
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================
# Depends on get_current_user, NOT get_settled_user - this is the one
# thing an account still holding a temporary password is allowed to do.

@router.post("/change-password", response_model=TokenResponse)
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your current password is not right.",
        )

    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=400,
            detail="Choose a password you have not used here before.",
        )

    problem = password_problem(payload.new_password)

    if problem:
        raise HTTPException(status_code=400, detail=problem)

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.must_change_password = False

    db.commit()
    db.refresh(current_user)

    # A fresh token, so a client that stored the old one does not keep
    # carrying a "you must change your password" state around.
    access_token = create_access_token(
        data={"sub": str(current_user.id), "role": current_user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        role=current_user.role.value,
        must_change_password=False,
        display_name=display_name_for(current_user, db),
    )


# ============================================================
# CURRENT USER
# ============================================================

@router.get("/me", response_model=AccountOut)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AccountOut(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value,
        login_id=current_user.login_id,
        must_change_password=current_user.must_change_password,
        display_name=display_name_for(current_user, db),
    )


# ============================================================
# PATIENT PROFILE
# ============================================================

@router.get("/patient/profile", response_model=PatientOut)
def get_patient_profile(
    current_user: User = Depends(get_current_user),
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    # A patient row created before health_id existed - assign one now
    # rather than showing a blank ID card. Written back immediately so
    # every later read (and any hospital lookup) sees the same value.
    if not current_patient.health_id:
        current_patient.health_id = generate_health_id(db)
        db.commit()
        db.refresh(current_patient)

    return PatientOut(
        id=current_patient.id,
        full_name=current_patient.full_name,
        age=current_patient.age,
        gender=current_patient.gender,
        mobile=current_patient.mobile,
        email=current_user.email,
        health_id=current_patient.health_id,
    )
