"""
The database side of the consent ledger.

Three things live here:

  record_event()  - called from the consent routes, INSIDE the same
                    database transaction that changes access_requests
  run_chain_check() / run_reconciliation() - the two integrity checks

The hashing itself is in app/core/ledger_hash.py.
"""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import LEDGER_HMAC_SECRET
from app.models.access_request import AccessRequest
from app.models.consent_event import ConsentEvent
from app.core.ledger_hash import (
    GENESIS_HASH,
    canonical_payload,
    compute_event_hash,
    find_status_mismatches,
    latest_event_per_request,
    make_ref,
    sign_event,
    verify_chain,
)

# Any fixed number; it just has to be the same everywhere so that all
# writers queue on the same lock.
_LEDGER_LOCK_KEY = 7340211


def record_event(
    db: Session,
    request: AccessRequest,
    event_type: str,
) -> ConsentEvent:
    """Append one event to the ledger.

    Does NOT commit - the caller commits, so the status change on
    access_requests and this ledger row are saved together or not at
    all. If recording fails the whole consent action fails, which is
    deliberate: a consent change with no ledger entry would be exactly
    the gap this feature exists to close.

    `request.id` must already exist, so on a brand-new request call
    db.flush() before this.
    """

    # Two consent actions at the same instant could otherwise both read
    # the same "last event" and both claim to follow it, splitting the
    # chain in two. The lock makes them queue; it is released
    # automatically when the transaction commits or rolls back.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": _LEDGER_LOCK_KEY},
        )

    last = (
        db.query(ConsentEvent)
        .order_by(ConsentEvent.seq.desc())
        .first()
    )

    prev_hash = last.event_hash if last is not None else GENESIS_HASH

    now = datetime.utcnow()
    patient_ref = make_ref(LEDGER_HMAC_SECRET, str(request.patient_id))
    doctor_ref = make_ref(LEDGER_HMAC_SECRET, str(request.doctor_id))

    payload = canonical_payload(
        request.id, event_type, patient_ref, doctor_ref, now
    )

    event_hash = compute_event_hash(prev_hash, payload)

    event = ConsentEvent(
        request_id=request.id,
        event_type=event_type,
        patient_ref=patient_ref,
        doctor_ref=doctor_ref,
        created_at=now,
        prev_hash=prev_hash,
        event_hash=event_hash,
        # Only code holding LEDGER_HMAC_SECRET can produce this.
        signature=sign_event(LEDGER_HMAC_SECRET, event_hash),
    )

    db.add(event)
    db.flush()

    return event


def run_chain_check(db: Session) -> dict:
    """Walk the whole ledger and confirm every link and hash."""

    events = db.query(ConsentEvent).order_by(ConsentEvent.seq.asc()).all()

    return verify_chain(events, LEDGER_HMAC_SECRET)


def run_reconciliation(db: Session) -> dict:
    """Compare the ledger's view of every request with the table's."""

    events = db.query(ConsentEvent).order_by(ConsentEvent.seq.asc()).all()
    latest = latest_event_per_request(events)

    table = {
        str(row.id): row.status
        for row in db.query(AccessRequest.id, AccessRequest.status).all()
    }

    return find_status_mismatches(latest, table)
