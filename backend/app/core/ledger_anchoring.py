"""
The database and scheduling side of Phases 2 and 3.

  Phase 3 - publish_next_anchor(), refresh_pending_anchors()
            put the ledger's fingerprint on a public chain.
  Phase 2 - build_integrity_report(), LedgerWorker
            check the ledger on a schedule and raise the alarm.

The decisions (what counts as tampering, what is just "couldn't check
right now") are made by the pure code in ledger_anchor.py, which has its
own tests. This file only fetches rows, calls it, and saves the result.
"""

import json
import threading
import urllib.request
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal, engine
from app.models.consent_event import ConsentEvent
from app.models.ledger_anchor import LedgerAnchor, LedgerCheck
from app.models.access_request import AccessRequest
from app.core.ledger_anchor import build_batch, verify_anchors
from app.core.ledger_hash import (
    find_status_mismatches,
    latest_event_per_request,
    verify_chain,
)
from app.core.ledger_providers import AnchorProviderError, build_provider

# Different from the lock key in ledger.py (that one serialises writers).
_WORKER_LOCK_KEY = 7340212

_provider = None
_provider_error = None


# ------------------------------------------------------------
# provider (built once)
# ------------------------------------------------------------

def get_provider():
    """The configured provider. If the configuration is wrong we fall
    back to 'none' and remember why, so the API still starts and the
    admin status page can say what to fix."""

    global _provider, _provider_error

    if _provider is None:
        try:
            _provider = build_provider(config.LEDGER_ANCHOR_CONFIG)
        except AnchorProviderError as error:
            _provider_error = str(error)
            print(f"[ledger] Anchoring is OFF: {error}")
            _provider = build_provider({"provider": "none"})

    return _provider


def provider_error():
    get_provider()
    return _provider_error


def anchor_to_dict(row: LedgerAnchor) -> dict:
    return {
        "from_seq": row.from_seq,
        "to_seq": row.to_seq,
        "event_count": row.event_count,
        "head_hash": row.head_hash,
        "merkle_root": row.merkle_root,
        "digest": row.digest,
        "status": row.status,
        "tx_id": row.tx_id,
    }


# ------------------------------------------------------------
# Phase 3: publishing
# ------------------------------------------------------------

def refresh_pending_anchors(db: Session, provider) -> int:
    """Move pending anchors to confirmed once the chain says so, and
    publish again if a transaction was lost. Returns how many changed."""

    if not provider.enabled:
        return 0

    changed = 0
    now = datetime.utcnow()
    stuck_after = timedelta(minutes=config.LEDGER_ANCHOR_STUCK_MINUTES)

    for row in db.query(LedgerAnchor).filter(LedgerAnchor.status == "pending").all():
        result = provider.check(anchor_to_dict(row))
        state = result.get("state")

        if state == "confirmed":
            row.status = "confirmed"
            row.block_number = result.get("block_number")
            row.confirmed_at = now
            changed += 1

        elif state == "missing" and now - row.published_at > stuck_after:
            # The transaction never made it into a block (dropped from
            # the mempool, fee too low...). Same digest, new attempt -
            # the row, and so the batch, stays as it was.
            try:
                republished = provider.publish(row.digest)
            except AnchorProviderError as error:
                row.last_error = f"republish failed: {error}"
                continue

            row.last_error = (
                f"previous transaction {row.tx_id} was never mined; "
                "published again"
            )
            row.tx_id = republished["tx_id"]
            row.published_at = now
            changed += 1

    db.commit()
    return changed


def publish_next_anchor(db: Session, provider, force: bool = False):
    """Anchor every event written since the last anchor, if it is time.

    Returns the new LedgerAnchor, or None if there was nothing to do.
    Raises AnchorProviderError if publishing failed - nothing is saved
    in that case, so the same events are simply tried again next round.
    """

    if not provider.enabled:
        return None

    last = db.query(LedgerAnchor).order_by(LedgerAnchor.to_seq.desc()).first()
    last_to = last.to_seq if last is not None else 0

    if (
        last is not None
        and not force
        and datetime.utcnow() - last.created_at
        < timedelta(minutes=config.LEDGER_ANCHOR_INTERVAL_MINUTES)
    ):
        return None

    events = (
        db.query(ConsentEvent)
        .filter(ConsentEvent.seq > last_to)
        .order_by(ConsentEvent.seq.asc())
        .limit(config.LEDGER_ANCHOR_MAX_EVENTS)
        .all()
    )

    batch = build_batch(events, config.LEDGER_ANCHOR_MAX_EVENTS)

    if batch is None:
        return None

    result = provider.publish(batch["digest"])  # may raise

    now = datetime.utcnow()
    row = LedgerAnchor(
        **batch,
        provider=provider.name,
        tx_id=result["tx_id"],
        status=result.get("state", "pending"),
        block_number=result.get("block_number"),
        created_at=now,
        published_at=now,
        confirmed_at=now if result.get("state") == "confirmed" else None,
    )
    db.add(row)
    db.commit()

    # A copy of the anchor outside the database. If someone later
    # deletes the anchor rows, this line (and the chain itself) remains.
    print(
        f"[ledger] anchored events {row.from_seq}-{row.to_seq} "
        f"({row.event_count}) tx={row.tx_id} digest={row.digest}"
    )

    return row


# ------------------------------------------------------------
# Phase 2: checking
# ------------------------------------------------------------

def build_integrity_report(db: Session, provider, full_onchain: bool = False) -> dict:
    """Everything an admin needs to know, in one dict.

    full_onchain=True asks the chain about EVERY anchor instead of just
    the newest ones - slower (one or more requests per anchor), meant
    for a manual audit.
    """

    events = db.query(ConsentEvent).order_by(ConsentEvent.seq.asc()).all()

    chain = verify_chain(events, config.LEDGER_HMAC_SECRET)

    table = {
        str(row.id): row.status
        for row in db.query(AccessRequest.id, AccessRequest.status).all()
    }
    reconcile = find_status_mismatches(latest_event_per_request(events), table)

    anchors = (
        db.query(LedgerAnchor).order_by(LedgerAnchor.to_seq.asc()).all()
    )
    anchor_dicts = [anchor_to_dict(a) for a in anchors]

    if not provider.enabled:
        onchain_for = set()
    elif full_onchain:
        onchain_for = set(range(len(anchor_dicts)))
    else:
        # The newest anchor, and the newest one already confirmed (the
        # newest may still be waiting for confirmations).
        onchain_for = set()
        if anchor_dicts:
            onchain_for.add(len(anchor_dicts) - 1)
            for i in range(len(anchor_dicts) - 1, -1, -1):
                if anchor_dicts[i]["status"] == "confirmed":
                    onchain_for.add(i)
                    break

    anchor_report = verify_anchors(
        events, anchor_dicts, provider.check, onchain_for=onchain_for
    )

    warnings = []

    if chain.get("legacy_unsigned"):
        warnings.append(
            f"{chain['legacy_unsigned']} events predate event signing and "
            "cannot be authenticated"
        )

    if not provider.enabled:
        anchor_report["unverified"].append(
            "anchoring is switched off - the ledger has no outside witness"
        )
        if provider_error():
            warnings.append(f"anchoring configuration problem: {provider_error()}")
    elif anchor_report["unanchored_events"]:
        newest = anchors[-1].created_at if anchors else None
        late = timedelta(minutes=config.LEDGER_ANCHOR_INTERVAL_MINUTES * 3)
        if newest is not None and datetime.utcnow() - newest > late:
            warnings.append(
                f"{anchor_report['unanchored_events']} events are waiting "
                "for an anchor and the last one is overdue"
            )

    healthy = (
        chain["ok"]
        and not reconcile["mismatched"]
        and not reconcile["orphaned"]
        and anchor_report["ok"]
    )

    return {
        "healthy": healthy,
        "checked_at": datetime.utcnow().isoformat(),
        "chain": chain,
        "reconciliation": reconcile,
        "anchors": anchor_report,
        "warnings": warnings,
    }


def _save_check(db: Session, report: dict) -> None:
    """Keep a short record of each scheduled check."""

    brief = {
        "chain": report["chain"],
        "mismatched": report["reconciliation"]["mismatched"][:20],
        "orphaned": report["reconciliation"]["orphaned"][:20],
        "anchor_problems": report["anchors"]["problems"][:20],
        "unverified": report["anchors"]["unverified"][:20],
        "unanchored_events": report["anchors"]["unanchored_events"],
        "warnings": report["warnings"],
    }

    db.add(LedgerCheck(healthy=report["healthy"], summary=json.dumps(brief)))
    db.commit()

    # Keep the latest 500.
    db.execute(
        text(
            "DELETE FROM ledger_checks WHERE id <= "
            "(SELECT COALESCE(MAX(id), 0) - 500 FROM ledger_checks)"
        )
    )
    db.commit()


def send_alert(message: str) -> None:
    """Slack-style webhook. Never raises - an alert failing must not
    stop the checks."""

    print(f"[ledger] ALERT: {message}")

    url = config.LEDGER_ALERT_WEBHOOK_URL
    if not url:
        return

    try:
        request = urllib.request.Request(
            url,
            data=json.dumps({"text": f"[consent ledger] {message}"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=10).read()
    except Exception as error:  # noqa: BLE001
        print(f"[ledger] could not send the alert ({error})")


# ------------------------------------------------------------
# the scheduler
# ------------------------------------------------------------

class LedgerWorker(threading.Thread):
    """Runs refresh -> anchor -> check, every few minutes.

    A thread inside the API process, so there is nothing extra to deploy
    and no new dependency. If several API workers run, each has one of
    these, but a Postgres advisory lock lets only one do the round.
    """

    def __init__(self):
        super().__init__(name="ledger-worker", daemon=True)
        self._stop_event = threading.Event()
        self._last_healthy = True
        self._last_alert = None

    def stop(self):
        self._stop_event.set()

    def run(self):
        # Let the API finish starting before the first round.
        if self._stop_event.wait(20):
            return

        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as error:  # noqa: BLE001
                print(f"[ledger] worker round failed ({type(error).__name__}: {error})")

            self._stop_event.wait(config.LEDGER_CHECK_INTERVAL_MINUTES * 60)

    def tick(self):
        provider = get_provider()

        with engine.connect() as lock_connection:
            got_lock = lock_connection.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": _WORKER_LOCK_KEY}
            ).scalar()

            if not got_lock:
                return  # another worker is doing this round

            try:
                self._round(provider)
            finally:
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:k)"), {"k": _WORKER_LOCK_KEY}
                )

    def _round(self, provider):
        db = SessionLocal()

        try:
            try:
                refresh_pending_anchors(db, provider)
            except Exception as error:  # noqa: BLE001
                db.rollback()
                print(f"[ledger] refreshing anchors failed ({error})")

            try:
                publish_next_anchor(db, provider)
            except AnchorProviderError as error:
                db.rollback()
                print(f"[ledger] could not publish an anchor ({error}); will retry")
            except Exception as error:  # noqa: BLE001
                db.rollback()
                print(f"[ledger] anchoring failed ({type(error).__name__}: {error})")

            report = build_integrity_report(db, provider)
            _save_check(db, report)
            self._maybe_alert(report)

        finally:
            db.close()

    def _maybe_alert(self, report: dict):
        now = datetime.utcnow()

        if report["healthy"]:
            if not self._last_healthy:
                send_alert("ledger is healthy again")
            self._last_healthy, self._last_alert = True, None
            return

        repeat = timedelta(minutes=config.LEDGER_ALERT_REPEAT_MINUTES)

        if self._last_healthy or self._last_alert is None or now - self._last_alert > repeat:
            reasons = []
            if not report["chain"]["ok"]:
                reasons.append(
                    f"chain broken at seq {report['chain']['broken_at_seq']}: "
                    f"{report['chain']['reason']}"
                )
            if report["reconciliation"]["mismatched"]:
                reasons.append(
                    f"{len(report['reconciliation']['mismatched'])} request(s) "
                    "whose status disagrees with the ledger"
                )
            if report["reconciliation"]["orphaned"]:
                reasons.append(
                    f"{len(report['reconciliation']['orphaned'])} ledger "
                    "event(s) for requests that no longer exist"
                )
            reasons.extend(report["anchors"]["problems"][:5])
            send_alert("INTEGRITY PROBLEM - " + "; ".join(reasons))
            self._last_alert = now

        self._last_healthy = False


_worker = None


def start_worker() -> None:
    """Called once at startup (see app/main.py)."""

    global _worker

    if not config.LEDGER_WORKER_ENABLED or _worker is not None:
        return

    _worker = LedgerWorker()
    _worker.start()

    print(
        f"[ledger] worker started: checks every "
        f"{config.LEDGER_CHECK_INTERVAL_MINUTES} min, anchoring via "
        f"'{get_provider().name}'"
    )


def stop_worker() -> None:
    global _worker

    if _worker is not None:
        _worker.stop()
        _worker = None
