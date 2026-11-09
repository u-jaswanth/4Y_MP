"""
Tiny, idempotent schema top-ups.

The project has no Alembic setup, and SQLAlchemy's create_all() only
creates missing TABLES - it never adds a missing COLUMN to a table that
already exists. So an existing database would keep working right up
until the first query touched `reports.ai_summary` and then fail with
"column does not exist".

These run once at startup (see app/main.py) and are safe to run any
number of times.
"""

from sqlalchemy import text

from app.database import engine, Base

# Importing the models registers them on Base.metadata so create_all
# can see them.
from app.models.user import User  # noqa: F401
from app.models.hospital import Hospital  # noqa: F401
from app.models.doctor import Doctor  # noqa: F401
from app.models.access_request import AccessRequest  # noqa: F401
from app.models.consent_event import ConsentEvent  # noqa: F401
from app.models.ledger_anchor import LedgerAnchor, LedgerCheck  # noqa: F401
from app.models.doctor_chat_message import DoctorChatMessage  # noqa: F401

_REPORT_COLUMNS = (
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_summary TEXT",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_summary_generated_at TIMESTAMP",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_summary_error TEXT",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS observation_count INTEGER",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS uploaded_by_hospital VARCHAR",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS uploaded_by_staff VARCHAR",
)

# `patients` predates the Health ID feature, so any database that
# already exists needs this topped up the same way.
_PATIENT_COLUMNS = (
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS health_id VARCHAR",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_patients_health_id "
    "ON patients (health_id)",
)


# The portal columns. `users` predates the admin/hospital/doctor
# portals, and `doctors` predates hospitals owning them, so both need
# topping up on any database that already exists.
_USER_COLUMNS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS login_id VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password "
    "BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active "
    "BOOLEAN NOT NULL DEFAULT TRUE",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_login_id ON users (login_id)",
)

_DOCTOR_COLUMNS = (
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS hospital_id UUID",
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS user_id UUID",
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS login_id VARCHAR",
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS email VARCHAR",
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS phone VARCHAR",
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS created_at TIMESTAMP",
    "CREATE INDEX IF NOT EXISTS ix_doctors_hospital_id "
    "ON doctors (hospital_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_doctors_login_id "
    "ON doctors (login_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_doctors_user_id "
    "ON doctors (user_id)",
)


def ensure_report_summary_columns() -> None:
    try:
        with engine.begin() as connection:
            for statement in _REPORT_COLUMNS:
                connection.execute(text(statement))

    except Exception as error:  # noqa: BLE001
        print(
            "[schema] Could not add the report summary columns automatically "
            f"({error}). Run the ALTER TABLE statements in "
            "app/core/db_migrations.py once as a DB admin."
        )


def ensure_patient_columns() -> None:
    """Add the Health ID column to `patients`.

    Same one-statement-per-transaction reasoning as ensure_portal_columns:
    the CREATE UNIQUE INDEX could fail independently of the ALTER TABLE.
    """

    for statement in _PATIENT_COLUMNS:
        try:
            with engine.begin() as connection:
                connection.execute(text(statement))

        except Exception as error:  # noqa: BLE001
            print(f"[schema] Skipped: {statement[:60]}... ({error})")


def ensure_doctor_table() -> None:
    """Create the `doctors` table if it isn't there yet."""

    try:
        Doctor.__table__.create(bind=engine, checkfirst=True)

    except Exception as error:  # noqa: BLE001
        print(f"[schema] Could not create the doctors table ({error}).")


def ensure_hospital_table() -> None:
    """Create the `hospitals` table if it isn't there yet.

    Runs before ensure_portal_columns, because the foreign key from
    `doctors.hospital_id` needs something to point at.
    """

    try:
        Hospital.__table__.create(bind=engine, checkfirst=True)

    except Exception as error:  # noqa: BLE001
        print(f"[schema] Could not create the hospitals table ({error}).")


def ensure_access_tables() -> None:
    """Create `access_requests` and `doctor_chat_messages` if missing.

    Both carry foreign keys into `doctors` and `patients`, so this must
    run after ensure_doctor_table() - same ordering reason as
    ensure_doctor_table() itself running after ensure_hospital_table().
    """

    try:
        AccessRequest.__table__.create(bind=engine, checkfirst=True)
    except Exception as error:  # noqa: BLE001
        print(f"[schema] Could not create the access_requests table ({error}).")

    try:
        DoctorChatMessage.__table__.create(bind=engine, checkfirst=True)
    except Exception as error:  # noqa: BLE001
        print(
            "[schema] Could not create the doctor_chat_messages table "
            f"({error})."
        )


def ensure_portal_columns() -> None:
    """Add the admin / hospital / doctor portal columns.

    Each statement runs in its own transaction. A CREATE UNIQUE INDEX
    can legitimately fail on a database that already holds duplicates,
    and one failure inside a shared transaction would roll back the
    ALTER TABLEs alongside it - which are the part that actually
    matters.
    """

    for statement in (*_USER_COLUMNS, *_DOCTOR_COLUMNS):
        try:
            with engine.begin() as connection:
                connection.execute(text(statement))

        except Exception as error:  # noqa: BLE001
            print(
                f"[schema] Skipped: {statement.split(' ADD COLUMN')[0][:60]}... "
                f"({error})"
            )


_LEDGER_APPEND_ONLY_STATEMENTS = (
    """
    CREATE OR REPLACE FUNCTION consent_events_block_change()
    RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'consent_events is append-only';
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS consent_events_no_change ON consent_events",
    """
    CREATE TRIGGER consent_events_no_change
    BEFORE UPDATE OR DELETE ON consent_events
    FOR EACH ROW EXECUTE FUNCTION consent_events_block_change()
    """,
    "DROP TRIGGER IF EXISTS consent_events_no_truncate ON consent_events",
    """
    CREATE TRIGGER consent_events_no_truncate
    BEFORE TRUNCATE ON consent_events
    FOR EACH STATEMENT EXECUTE FUNCTION consent_events_block_change()
    """,
)


def ensure_ledger_table() -> None:
    """Create `consent_events` and make it append-only.

    The trigger is a second line of defence: the app never updates or
    deletes ledger rows anyway, but this stops an accidental or casual
    UPDATE / DELETE / TRUNCATE straight in the database. It does NOT
    stop someone with ownership of the table from dropping the trigger,
    which is why the blockchain anchor (a later phase) exists.

    Safe to run on every startup.
    """

    try:
        ConsentEvent.__table__.create(bind=engine, checkfirst=True)

    except Exception as error:  # noqa: BLE001
        print(f"[schema] Could not create the consent_events table ({error}).")
        return

    # Event signatures: create_all() never adds a column to an existing
    # table. Existing rows keep NULL (= legacy / unsigned); they are not
    # given invented signatures. ALTER TABLE does not fire the
    # append-only row triggers.
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE consent_events "
                    "ADD COLUMN IF NOT EXISTS signature VARCHAR(64)"
                )
            )

    except Exception as error:  # noqa: BLE001
        print(
            "[schema] Could not add consent_events.signature "
            f"({error}). Run the ALTER TABLE in app/core/db_migrations.py "
            "once as a DB admin; until then ledger writes will fail."
        )

    for statement in _LEDGER_APPEND_ONLY_STATEMENTS:
        try:
            with engine.begin() as connection:
                # exec_driver_sql: no bind-parameter parsing, so the
                # $$ ... $$ function body is passed through untouched.
                connection.exec_driver_sql(statement)

        except Exception as error:  # noqa: BLE001
            print(
                "[schema] Could not install the append-only trigger "
                f"({error}). The ledger still works; it just is not "
                "protected at the database level."
            )
            return


def ensure_ledger_anchor_tables() -> None:
    """Create `ledger_anchors` and `ledger_checks` (Phases 2 and 3).

    Unlike consent_events these are ordinary tables: an anchor changes
    from pending to confirmed, and old check results are pruned. Nothing
    in them is trusted without being re-checked against the events and
    the blockchain.
    """

    for model in (LedgerAnchor, LedgerCheck):
        try:
            model.__table__.create(bind=engine, checkfirst=True)

        except Exception as error:  # noqa: BLE001
            print(f"[schema] Could not create {model.__tablename__} ({error}).")
