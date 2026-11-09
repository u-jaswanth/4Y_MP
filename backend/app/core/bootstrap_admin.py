"""
The one admin account.

There is no sign-up page for an admin, and no endpoint that creates
one - the platform would be wide open if there were. Instead this runs
at startup and makes sure exactly one account with role=admin exists,
using ADMIN_EMAIL and ADMIN_PASSWORD from the environment.

Behaviour is deliberately narrow:

  * No admin in the database  -> create one from the env values.
  * An admin already exists   -> leave it completely alone.

That second rule is the important one. It means changing ADMIN_PASSWORD
in .env does NOT change the password of a running deployment, so the
env file is not a way in for anyone who reads it later, and an admin
who has changed their password does not silently get reset back to the
default on the next restart. To move the password, sign in and use
POST /auth/change-password.
"""

from sqlalchemy.orm import Session

from app.config import ADMIN_EMAIL, ADMIN_PASSWORD
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.auth.security import hash_password

DEFAULT_ADMIN_PASSWORD = "ChangeMe@2026"


def ensure_admin_account(db: Session | None = None) -> None:

    own_session = db is None
    session = db or SessionLocal()

    try:
        existing = (
            session.query(User)
            .filter(User.role == UserRole.admin)
            .first()
        )

        if existing is not None:
            return

        email = (ADMIN_EMAIL or "admin@mediconnect.ai").strip().lower()
        password = ADMIN_PASSWORD or DEFAULT_ADMIN_PASSWORD

        # An email collision means someone already registered as a
        # patient with the address meant for the admin. Say so rather
        # than crashing the whole startup on a unique constraint.
        clash = session.query(User).filter(User.email == email).first()

        if clash is not None:
            print(
                f"[admin] {email} is already registered as a "
                f"{clash.role.value}. Set ADMIN_EMAIL to a different "
                "address and restart."
            )
            return

        admin = User(
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.admin,
            login_id="ADMIN",
            # The admin is expected to change this immediately, and the
            # portal sends them to the password screen until they do.
            must_change_password=(password == DEFAULT_ADMIN_PASSWORD),
            is_active=True,
        )

        session.add(admin)
        session.commit()

        print(f"[admin] Admin account ready: {email}")

        if password == DEFAULT_ADMIN_PASSWORD:
            print(
                "[admin] Using the built-in default password. Sign in and "
                "change it - the portal will ask you to."
            )

    except Exception as error:  # noqa: BLE001
        session.rollback()
        print(f"[admin] Could not prepare the admin account ({error}).")

    finally:
        if own_session:
            session.close()
