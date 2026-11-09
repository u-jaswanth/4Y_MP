"""
Generating the IDs and temporary passwords that get handed out.

A hospital account is created by the admin, and a doctor account is
created by their hospital. In both cases a human reads the credentials
off a screen and types them somewhere else, so both are built from an
alphabet with the characters that get misread removed: no 0/O, no 1/I/L
and no 5/S.

Temporary passwords are generated with `secrets`, are never stored in
plain text, and are returned exactly once - in the response to the call
that created the account. Nothing reads them back afterwards. If they
are lost, the account has to be issued a new one (POST
/admin/hospitals/{id}/reset-password, POST
/hospital/doctors/{id}/reset-password), which is also the only reason
those two endpoints exist.
"""

import re
import secrets
import uuid

from sqlalchemy.orm import Session

# No 0 O 1 I L 5 S.
_ID_ALPHABET = "ABCDEFGHJKMNPQRTUVWXYZ2346789"

# Passwords add lower case and a couple of symbols, still avoiding the
# ambiguous pairs.
_PASSWORD_ALPHABET = (
    "ABCDEFGHJKMNPQRTUVWXYZ"
    "abcdefghijkmnpqrtuvwxyz"
    "23456789"
    "@#%+=?"
)

HOSPITAL_PREFIX = "HOSP"
DOCTOR_PREFIX = "DOC"


def _random_id(prefix: str, length: int = 6) -> str:
    body = "".join(secrets.choice(_ID_ALPHABET) for _ in range(length))
    return f"{prefix}-{body}"


def generate_login_id(db: Session, prefix: str) -> str:
    """A login ID that is not already taken.

    Imported here rather than at module level to keep this file free of
    a circular import back through app.models.
    """

    from app.models.user import User

    for _ in range(20):
        candidate = _random_id(prefix)

        taken = (
            db.query(User)
            .filter(User.login_id == candidate)
            .first()
        )

        if taken is None:
            return candidate

    # 29^6 is about 594 million, so twenty collisions in a row means
    # something is wrong rather than unlucky. Fall back to something
    # certainly unique instead of looping forever.
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


_HEALTH_ID_LENGTH = 12


def generate_health_id(db: Session) -> str:
    """A 12-digit Health ID that is not already taken.

    Unlike the hospital/doctor login IDs this is read by a person off
    their own phone and typed by someone else (or scanned), not
    memorised, so it uses plain digits rather than the letters-minus-
    ambiguous-characters alphabet above - digits group cleanly into
    "9214 7736 0025" and match what the QR code on the patient
    dashboard encodes.
    """

    from app.models.patient import Patient

    for _ in range(20):
        candidate = "".join(
            secrets.choice("0123456789") for _ in range(_HEALTH_ID_LENGTH)
        )

        taken = (
            db.query(Patient)
            .filter(Patient.health_id == candidate)
            .first()
        )

        if taken is None:
            return candidate

    # See the comment on generate_login_id above - this branch means
    # something is wrong, not just unlucky.
    return uuid.uuid4().hex[:_HEALTH_ID_LENGTH]


def generate_temporary_password(length: int = 12) -> str:
    """A throwaway password the person is forced to replace on first login."""

    while True:
        password = "".join(
            secrets.choice(_PASSWORD_ALPHABET) for _ in range(length)
        )

        # Make sure it actually satisfies the same rule we enforce on
        # the password the person chooses to replace it with.
        if (
            any(character.islower() for character in password)
            and any(character.isupper() for character in password)
            and any(character.isdigit() for character in password)
        ):
            return password


def generate_doctor_slug(db: Session, full_name: str) -> str:
    """A unique, readable slug for a hospital-created doctor.

    `doctors.slug` is NOT NULL and unique because the seed file keys on
    it. Doctors added through a portal still need one, so it is built
    from the name with a short random suffix - "Dr. Anjali Rao" becomes
    something like `anjali-rao-k7m2`.
    """

    from app.models.doctor import Doctor

    base = full_name.lower().strip()

    # Drop a leading "dr" / "dr." so every slug doesn't start the same.
    base = re.sub(r"^dr\.?\s+", "", base)

    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")

    if not base:
        base = "doctor"

    base = base[:40]

    for _ in range(20):
        suffix = "".join(secrets.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(4))
        candidate = f"{base}-{suffix}"

        taken = (
            db.query(Doctor)
            .filter(Doctor.slug == candidate)
            .first()
        )

        if taken is None:
            return candidate

    return f"{base}-{uuid.uuid4().hex[:8]}"


# ================================================================
# PASSWORD RULES
# ================================================================

MIN_PASSWORD_LENGTH = 8


def password_problem(password: str) -> str | None:
    """Return why this password is not acceptable, or None if it is.

    Deliberately short: length, plus one of each kind of character.
    Anything stricter tends to push people towards writing the password
    on a sticky note, which is the thing the forced first-login change
    is trying to avoid in the first place.
    """

    if len(password or "") < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."

    if not any(character.isalpha() for character in password):
        return "Include at least one letter."

    if not any(character.isdigit() for character in password):
        return "Include at least one number."

    return None
