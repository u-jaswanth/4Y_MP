"""
The pure logic of the consent ledger - no database, no web framework.

Kept separate from app/core/ledger.py (which talks to Postgres) so this
file can be read, tested and reasoned about on its own. Everything here
is a plain function of its inputs.

The idea in one paragraph: every consent action becomes an "event". An
event's hash is SHA-256 over (the previous event's hash + this event's
content). Because each hash includes the one before it, editing or
deleting any old event changes every hash after it - and verify_chain()
notices.
"""

import hashlib
import hmac
import json
from datetime import datetime


# The "previous hash" of the very first event ever recorded.
GENESIS_HASH = "0" * 64


class EventType:
    """Plain string constants, same style as AccessStatus."""

    REQUESTED = "requested"
    APPROVED = "approved"
    DENIED = "denied"
    REVOKED = "revoked"


# What access_requests.status should be once a given event is the
# LATEST one for that request. Used by the reconciliation check.
STATUS_AFTER_EVENT = {
    EventType.REQUESTED: "pending",
    EventType.APPROVED: "approved",
    EventType.DENIED: "denied",
    EventType.REVOKED: "revoked",
}


# ------------------------------------------------------------
# Building an event
# ------------------------------------------------------------

def make_ref(secret: str, value: str) -> str:
    """A keyed fingerprint (HMAC-SHA256) of an ID.

    The ledger stores this instead of the raw patient / doctor UUID, so
    that nobody reading it can work out whose consent it is by hashing
    guessed IDs - they would need the secret too.
    """

    return hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def format_timestamp(moment: datetime) -> str:
    """One fixed text form for a time.

    Always includes microseconds, so the same moment never turns into
    two different strings (and therefore two different hashes) just
    because its microseconds happened to be zero.
    """

    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")


def canonical_payload(
    request_id: str,
    event_type: str,
    patient_ref: str,
    doctor_ref: str,
    created_at: datetime,
) -> str:
    """The exact text that gets hashed.

    sort_keys + fixed separators mean the same data ALWAYS produces the
    same text, so the same hash. Nothing sensitive goes in here - no
    names, no doctor note, no report content.
    """

    return json.dumps(
        {
            "request_id": str(request_id),
            "type": event_type,
            "patient_ref": patient_ref,
            "doctor_ref": doctor_ref,
            "ts": format_timestamp(created_at),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_event_hash(prev_hash: str, payload: str) -> str:
    return hashlib.sha256((prev_hash + "|" + payload).encode("utf-8")).hexdigest()


# Prefix that keeps event signatures separate from make_ref() values,
# which use the same secret.
SIGNATURE_DOMAIN = "consent-event-signature-v1|"


def sign_event(secret: str, event_hash: str) -> str:
    """HMAC-SHA256 over an event's hash - proof the application wrote it.

    event_hash already covers prev_hash and every field of the event, so
    signing it binds the event's content AND its position in the chain.
    The hash alone proves nothing about who wrote the event (anyone can
    compute it); this does, because it needs the secret.
    """

    return hmac.new(
        secret.encode("utf-8"),
        (SIGNATURE_DOMAIN + event_hash).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_event_signature(secret: str, event_hash: str, signature) -> bool:
    """True only for a non-empty signature that matches (constant time)."""

    if not signature:
        return False

    return hmac.compare_digest(
        sign_event(secret, event_hash).encode("utf-8"),
        str(signature).encode("utf-8"),
    )


# ------------------------------------------------------------
# Checking the chain
# ------------------------------------------------------------

def verify_chain(events, secret: str = None) -> dict:
    """Walk events in order and confirm the chain is intact.

    `events` is anything iterable whose items have these attributes:
    seq, request_id, event_type, patient_ref, doctor_ref, created_at,
    prev_hash, event_hash (and `signature`, when `secret` is given) - a
    ConsentEvent row, or a test stand-in. They must already be sorted
    by seq.

    Two things are checked for every event:
      1. prev_hash really is the previous event's event_hash
         (catches deleted / reordered / inserted-in-the-middle rows)
      2. event_hash really is the hash of this event's own content
         (catches an edited row)

    If `secret` is given, a third check runs:
      3. the event carries a valid HMAC signature (see sign_event)
         (catches an event INSERTed straight into the database: its
         hash can be computed by anyone, its signature cannot)

    Events from before signing existed have signature NULL. They are
    accepted as "legacy" ONLY while no signed event has been seen yet,
    i.e. as an unbroken prefix of the chain. Once one signed event
    appears, an unsigned event after it is treated as forged - otherwise
    an attacker could simply leave the signature empty.

    NOTE: this cannot detect events removed from the very END of the
    chain, or a complete rewrite where every hash is recomputed. Only
    comparing against a hash published outside the database (the
    blockchain anchor, Phase 3) can catch those.
    """

    expected_prev = GENESIS_HASH
    checked = 0
    signed = 0
    legacy_unsigned = 0
    signing_started = False

    for event in events:
        if event.prev_hash != expected_prev:
            return {
                "ok": False,
                "checked": checked,
                "broken_at_seq": event.seq,
                "reason": "prev_hash does not match the previous event "
                          "(an event was removed, reordered or inserted)",
            }

        payload = canonical_payload(
            event.request_id,
            event.event_type,
            event.patient_ref,
            event.doctor_ref,
            event.created_at,
        )

        if compute_event_hash(event.prev_hash, payload) != event.event_hash:
            return {
                "ok": False,
                "checked": checked,
                "broken_at_seq": event.seq,
                "reason": "event content does not match its hash "
                          "(the event was edited)",
            }

        if secret is not None:
            signature = getattr(event, "signature", None)

            if signature is None and not signing_started:
                legacy_unsigned += 1

            elif signature is None:
                return _forged(
                    event, checked,
                    "event has no signature but earlier events are signed "
                    "(it was not created by the application - forged)",
                )

            elif not verify_event_signature(secret, event.event_hash, signature):
                return _forged(
                    event, checked,
                    "event signature is invalid "
                    "(it was not created by the application - forged)",
                )

            else:
                signing_started = True
                signed += 1

        expected_prev = event.event_hash
        checked += 1

    return {
        "ok": True,
        "checked": checked,
        "broken_at_seq": None,
        "reason": "chain is intact",
        "signatures_verified": secret is not None,
        "signed": signed,
        "legacy_unsigned": legacy_unsigned,
    }


def _forged(event, checked: int, reason: str) -> dict:
    return {
        "ok": False,
        "checked": checked,
        "broken_at_seq": event.seq,
        "reason": reason,
        "request_id": str(event.request_id),
        "event_hash": event.event_hash,
    }


# ------------------------------------------------------------
# Comparing the ledger with the access_requests table
# ------------------------------------------------------------

def latest_event_per_request(events) -> dict:
    """{request_id: event_type of that request's newest event}.

    `events` must be sorted by seq so the last one seen wins.
    """

    latest = {}

    for event in events:
        latest[str(event.request_id)] = event.event_type

    return latest


def find_status_mismatches(latest_events: dict, table_statuses: dict) -> dict:
    """Compare what the ledger says with what access_requests says.

    latest_events:  {request_id: newest event type}
    table_statuses: {request_id: current access_requests.status}

    Returns:
      mismatched - requests where the two disagree (a status changed
                   with no matching event: the "attacker flips only the
                   table" case)
      unledgered - requests with NO events at all. Expected for rows
                   that existed before the ledger shipped; suspicious
                   for anything created afterwards.
      orphaned   - events whose request no longer exists in the table
    """

    mismatched = []
    unledgered = []

    for request_id, status in table_statuses.items():
        event_type = latest_events.get(request_id)

        if event_type is None:
            unledgered.append(request_id)
            continue

        expected = STATUS_AFTER_EVENT.get(event_type)

        if expected != status:
            mismatched.append(
                {
                    "request_id": request_id,
                    "ledger_says": expected,
                    "table_says": status,
                }
            )

    orphaned = [rid for rid in latest_events if rid not in table_statuses]

    return {
        "mismatched": mismatched,
        "unledgered": unledgered,
        "orphaned": orphaned,
    }
