from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.hospital import Hospital
from app.models.doctor import Doctor
from app.auth.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)

    if payload is None:
        raise credentials_error

    user_id = payload.get("sub")

    if user_id is None:
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    return user


def get_settled_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """A user who is past the forced first-login password change.

    Every portal endpoint depends on this rather than on
    `get_current_user`, so an account still sitting on its issued
    temporary password can do exactly two things: read /auth/me, and
    change its password. It cannot add doctors, read a patient list, or
    anything else, even if the client skips the redirect.
    """

    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Set a new password before using your account."
            ),
        )

    return current_user


def require_role(*roles: UserRole):
    """Dependency factory: allow only these roles, and only settled ones."""

    allowed = set(roles)

    def guard(current_user: User = Depends(get_settled_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account does not have access to this area.",
            )

        return current_user

    return guard


# ================================================================
# PER-ROLE PROFILE LOOKUPS
# ================================================================

def get_current_patient(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Patient:
    patient = (
        db.query(Patient)
        .filter(Patient.user_id == current_user.id)
        .first()
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patient profile found for this user",
        )

    return patient


def get_current_hospital(
    current_user: User = Depends(require_role(UserRole.hospital)),
    db: Session = Depends(get_db),
) -> Hospital:
    hospital = (
        db.query(Hospital)
        .filter(Hospital.user_id == current_user.id)
        .first()
    )

    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hospital profile found for this account.",
        )

    if not hospital.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This hospital account has been deactivated.",
        )

    return hospital


def get_current_doctor(
    current_user: User = Depends(require_role(UserRole.doctor)),
    db: Session = Depends(get_db),
) -> Doctor:
    doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == current_user.id)
        .first()
    )

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No doctor profile found for this account.",
        )

    return doctor
