"""
The patient's half of the doctor-access flow.

A doctor can only ever read a patient's record after the patient
approves a request here - see app/doctors/patient_access.py for the
doctor's side, which gates every read on an APPROVED row from this
same table.

Three actions, and each one only ever touches a row that belongs to
the current patient - `_owned_request()` enforces that on every call,
so a patient can never approve, deny or revoke a request addressed to
someone else even if they guess another request's id.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.access_request import AccessRequest, AccessStatus
from app.models.consent_event import ConsentEvent
from app.models.ledger_anchor import LedgerAnchor
from app.core.ledger import record_event
from app.core.ledger_hash import EventType
from app.core.ledger_merkle import merkle_proof, verify_proof
from app.core.ledger_anchoring import get_provider
from app.auth.dependencies import get_current_patient
from app.schemas.access import (
    AccessRequestOut,
    AccessRequestsOut,
    AnchorBrief,
    ConsentEventOut,
    ConsentHistoryItem,
    DoctorBrief,
    ReceiptOut,
)

router = APIRouter(prefix="/access", tags=["access"])


# ============================================================
# HELPERS
# ============================================================

def _owned_request(
    request_id: str, patient: Patient, db: Session
) -> AccessRequest:
    request = (
        db.query(AccessRequest)
        .filter(AccessRequest.id == request_id)
        .filter(AccessRequest.patient_id == patient.id)
        .first()
    )

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="No such access request.",
        )

    return request


def _events_with_anchors(events: list, db: Session) -> list:
    """ConsentEventOut for each event, with its blockchain anchor (if
    one covers it yet) attached."""

    if not events:
        return []

    low = min(e.seq for e in events)
    high = max(e.seq for e in events)

    anchors = (
        db.query(LedgerAnchor)
        .filter(LedgerAnchor.to_seq >= low)
        .filter(LedgerAnchor.from_seq <= high)
        .all()
    )

    provider = get_provider()
    out = []

    for event in events:
        covering = next(
            (a for a in anchors if a.from_seq <= event.seq <= a.to_seq), None
        )

        item = ConsentEventOut.model_validate(event)

        if covering is not None:
            item.anchor = AnchorBrief(
                status=covering.status,
                provider=covering.provider,
                tx_id=covering.tx_id,
                explorer_url=provider.explorer_url(covering.tx_id),
                published_at=covering.published_at,
            )

        out.append(item)

    return out


# ============================================================
# LIST (what's waiting on me, and what's already granted)
# ============================================================

@router.get("/requests", response_model=AccessRequestsOut)
def list_access_requests(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AccessRequest)
        .filter(AccessRequest.patient_id == current_patient.id)
        .filter(
            AccessRequest.status.in_(
                [AccessStatus.PENDING, AccessStatus.APPROVED]
            )
        )
        .order_by(AccessRequest.created_at.desc())
        .all()
    )

    pending = [row for row in rows if row.status == AccessStatus.PENDING]
    active = [row for row in rows if row.status == AccessStatus.APPROVED]

    return AccessRequestsOut(pending=pending, active=active)


# ============================================================
# APPROVE
# ============================================================

@router.post("/requests/{request_id}/approve", response_model=AccessRequestOut)
def approve_access_request(
    request_id: str,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    request = _owned_request(request_id, current_patient, db)

    if request.status != AccessStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="This request is no longer pending.",
        )

    request.status = AccessStatus.APPROVED
    request.decided_at = datetime.utcnow()

    # Same transaction as the status change above: both are saved by
    # the commit below, or neither is.
    record_event(db, request, EventType.APPROVED)

    db.commit()
    db.refresh(request)

    return request


# ============================================================
# DENY
# ============================================================

@router.post("/requests/{request_id}/deny", response_model=AccessRequestOut)
def deny_access_request(
    request_id: str,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    request = _owned_request(request_id, current_patient, db)

    if request.status != AccessStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="This request is no longer pending.",
        )

    request.status = AccessStatus.DENIED
    request.decided_at = datetime.utcnow()

    # Same transaction as the status change above: both are saved by
    # the commit below, or neither is.
    record_event(db, request, EventType.DENIED)

    db.commit()
    db.refresh(request)

    return request


# ============================================================
# REVOKE (an already-approved doctor)
# ============================================================

@router.post("/requests/{request_id}/revoke", response_model=AccessRequestOut)
def revoke_access(
    request_id: str,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    request = _owned_request(request_id, current_patient, db)

    if request.status != AccessStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="This doctor does not currently have access.",
        )

    request.status = AccessStatus.REVOKED
    request.decided_at = datetime.utcnow()

    # Same transaction as the status change above: both are saved by
    # the commit below, or neither is.
    record_event(db, request, EventType.REVOKED)

    db.commit()
    db.refresh(request)

    return request


# ============================================================
# HISTORY (every step of one request, from the ledger)
# ============================================================

@router.get(
    "/requests/{request_id}/history",
    response_model=list[ConsentEventOut],
)
def request_history(
    request_id: str,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    # _owned_request raises 404 unless this request is the current
    # patient's, so one patient can never read another's history.
    request = _owned_request(request_id, current_patient, db)

    events = (
        db.query(ConsentEvent)
        .filter(ConsentEvent.request_id == request.id)
        .order_by(ConsentEvent.seq.asc())
        .all()
    )

    return _events_with_anchors(events, db)


# ============================================================
# FULL HISTORY (every request this patient has ever had)
# ============================================================

@router.get("/history", response_model=list[ConsentHistoryItem])
def consent_history(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """All of the current patient's requests - denied and revoked ones
    too, which /requests leaves out - each with its ledger events.

    Requests from before the ledger existed come back with an empty
    `events` list; the page says so rather than hiding them.
    """

    requests = (
        db.query(AccessRequest)
        .filter(AccessRequest.patient_id == current_patient.id)
        .order_by(AccessRequest.created_at.desc())
        .all()
    )

    events_by_request: dict = {}

    if requests:
        events = (
            db.query(ConsentEvent)
            .filter(ConsentEvent.request_id.in_([r.id for r in requests]))
            .order_by(ConsentEvent.seq.asc())
            .all()
        )

        outs = _events_with_anchors(events, db)

        for event, out in zip(events, outs):
            events_by_request.setdefault(event.request_id, []).append(out)

    return [
        ConsentHistoryItem(
            request_id=row.id,
            status=row.status,
            created_at=row.created_at,
            doctor=(
                DoctorBrief.model_validate(row.doctor)
                if row.doctor is not None
                else None
            ),
            events=events_by_request.get(row.id, []),
        )
        for row in requests
    ]


# ============================================================
# RECEIPT (proof that one step is covered by the blockchain anchor)
# ============================================================

@router.get("/receipt/{event_hash}", response_model=ReceiptOut)
def event_receipt(
    event_hash: str,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """The proof for one step of the current patient's own history.

    Only events belonging to this patient's requests are found; any
    other hash is a 404, so this cannot be used to probe the ledger.
    """

    event = (
        db.query(ConsentEvent)
        .filter(ConsentEvent.event_hash == event_hash)
        .first()
    )

    owned = (
        event is not None
        and db.query(AccessRequest.id)
        .filter(AccessRequest.id == event.request_id)
        .filter(AccessRequest.patient_id == current_patient.id)
        .first()
        is not None
    )

    if not owned:
        raise HTTPException(status_code=404, detail="No such receipt.")

    base = dict(
        event_hash=event.event_hash,
        event_type=event.event_type,
        created_at=event.created_at,
    )

    anchor = (
        db.query(LedgerAnchor)
        .filter(LedgerAnchor.from_seq <= event.seq)
        .filter(LedgerAnchor.to_seq >= event.seq)
        .first()
    )

    if anchor is None:
        return ReceiptOut(
            **base,
            anchored=False,
            detail="This step is recorded and chained, but has not been "
            "published to the blockchain yet. Anchors are published on a "
            "schedule - check again later.",
        )

    batch_hashes = [
        row.event_hash
        for row in db.query(ConsentEvent.event_hash)
        .filter(ConsentEvent.seq >= anchor.from_seq)
        .filter(ConsentEvent.seq <= anchor.to_seq)
        .order_by(ConsentEvent.seq.asc())
        .all()
    ]

    try:
        index = batch_hashes.index(event.event_hash)
        proof = merkle_proof(batch_hashes, index)
        proof_valid = verify_proof(event.event_hash, proof, anchor.merkle_root)
    except ValueError:
        proof, proof_valid = [], False

    return ReceiptOut(
        **base,
        anchored=True,
        status=anchor.status,
        provider=anchor.provider,
        tx_id=anchor.tx_id,
        explorer_url=get_provider().explorer_url(anchor.tx_id),
        from_seq=anchor.from_seq,
        to_seq=anchor.to_seq,
        head_hash=anchor.head_hash,
        merkle_root=anchor.merkle_root,
        digest=anchor.digest,
        proof=proof,
        proof_valid=proof_valid,
    )
