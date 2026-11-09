"""
Admin-only tools for the consent ledger.

    GET  /admin/ledger/verify   run every check right now
    GET  /admin/ledger/status   what the scheduled checks last found,
                                and the recent blockchain anchors
    POST /admin/ledger/anchor   publish an anchor now instead of waiting

Nothing here changes consent data.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models.user import UserRole
from app.models.ledger_anchor import LedgerAnchor, LedgerCheck
from app.auth.dependencies import require_role
from app.core.ledger_anchoring import (
    build_integrity_report,
    get_provider,
    provider_error,
    publish_next_anchor,
    refresh_pending_anchors,
)
from app.core.ledger_providers import AnchorProviderError

router = APIRouter(
    prefix="/admin/ledger",
    tags=["ledger"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


def _anchor_out(row: LedgerAnchor, provider) -> dict:
    return {
        "from_seq": row.from_seq,
        "to_seq": row.to_seq,
        "event_count": row.event_count,
        "digest": row.digest,
        "status": row.status,
        "provider": row.provider,
        "tx_id": row.tx_id,
        "explorer_url": provider.explorer_url(row.tx_id),
        "block_number": row.block_number,
        "published_at": row.published_at,
        "confirmed_at": row.confirmed_at,
        "note": row.last_error,
    }


@router.get("/verify")
def verify_ledger(full: bool = False, db: Session = Depends(get_db)):
    """Run every check now.

    `?full=true` asks the blockchain about every anchor, not just the
    newest - slower, meant for an audit.
    """

    report = build_integrity_report(db, get_provider(), full_onchain=full)

    # Same shape as Phase 1 (healthy / chain / reconciliation), plus the
    # anchor section and warnings.
    return report


@router.get("/status")
def ledger_status(db: Session = Depends(get_db)):
    provider = get_provider()

    last_check = db.query(LedgerCheck).order_by(LedgerCheck.id.desc()).first()
    recent_checks = (
        db.query(LedgerCheck).order_by(LedgerCheck.id.desc()).limit(20).all()
    )
    anchors = (
        db.query(LedgerAnchor).order_by(LedgerAnchor.to_seq.desc()).limit(10).all()
    )

    return {
        "worker_enabled": config.LEDGER_WORKER_ENABLED,
        "check_interval_minutes": config.LEDGER_CHECK_INTERVAL_MINUTES,
        "anchoring": {
            "provider": provider.name,
            "enabled": provider.enabled,
            "configuration_problem": provider_error(),
            "interval_minutes": config.LEDGER_ANCHOR_INTERVAL_MINUTES,
            # Where an outsider can look the anchors up themselves.
            "pinned_address": getattr(provider, "address", None),
            "chain_id": getattr(provider, "chain_id", None),
        },
        "last_check": (
            {
                "ran_at": last_check.ran_at,
                "healthy": last_check.healthy,
                "details": json.loads(last_check.summary),
            }
            if last_check is not None
            else None
        ),
        "recent_checks": [
            {"ran_at": c.ran_at, "healthy": c.healthy} for c in recent_checks
        ],
        "latest_anchors": [_anchor_out(a, provider) for a in anchors],
    }


@router.post("/anchor")
def anchor_now(db: Session = Depends(get_db)):
    """Publish an anchor immediately (ignores the interval)."""

    provider = get_provider()

    if not provider.enabled:
        raise HTTPException(
            status_code=400,
            detail=provider_error() or "Anchoring is switched off "
            "(set LEDGER_ANCHOR_PROVIDER).",
        )

    try:
        refresh_pending_anchors(db, provider)
        row = publish_next_anchor(db, provider, force=True)

    except AnchorProviderError as error:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Could not publish: {error}")

    if row is None:
        return {"published": False, "detail": "No new events since the last anchor."}

    return {"published": True, "anchor": _anchor_out(row, provider)}
