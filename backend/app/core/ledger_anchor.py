"""
The pure logic of blockchain anchoring - no database, no network.

An ANCHOR is a single 32-byte digest that gets published to a public
chain. It commits to a batch of consecutive ledger events:

    digest = SHA-256( version | from_seq | to_seq | head_hash | root )

    head_hash  the event_hash of the newest event in the batch. Because
               every event_hash includes the one before it, this one
               value commits to ALL history up to that point.
    root       the Merkle root of the batch (see ledger_merkle.py), so
               individual events can be proven with a short proof.

Once the digest is on a public chain, nobody - including whoever owns
the database - can rewrite the past or cut the tail off without the
stored digest and the database disagreeing. verify_anchors() below is
that comparison.

What an anchor still cannot do: events written AFTER the newest anchor
are not covered until the next anchor is published. That window is the
anchor interval (LEDGER_ANCHOR_INTERVAL_MINUTES).
"""

import hashlib

from app.core.ledger_merkle import merkle_root

ANCHOR_VERSION = "consent-ledger-anchor-v1"

# Bytes put in front of the digest inside the blockchain transaction,
# so the transaction is recognisable as a ledger anchor.
ONCHAIN_MAGIC = b"CLG1"


def anchor_digest(
    from_seq: int, to_seq: int, head_hash: str, root: str
) -> str:
    text = f"{ANCHOR_VERSION}|{from_seq}|{to_seq}|{head_hash}|{root}"

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def onchain_payload(digest: str) -> bytes:
    """Exactly the bytes that go into the blockchain transaction."""

    return ONCHAIN_MAGIC + bytes.fromhex(digest)


def build_batch(events: list, max_events: int = 5000):
    """Describe the next anchor for `events`.

    `events` must be sorted by seq and must contain only events NOT
    yet covered by an anchor. Returns None if there is nothing to anchor.
    """

    batch = events[:max_events]

    if not batch:
        return None

    hashes = [e.event_hash for e in batch]
    root = merkle_root(hashes)
    head = batch[-1].event_hash
    from_seq = batch[0].seq
    to_seq = batch[-1].seq

    return {
        "from_seq": from_seq,
        "to_seq": to_seq,
        "event_count": len(batch),
        "head_hash": head,
        "merkle_root": root,
        "digest": anchor_digest(from_seq, to_seq, head, root),
    }


def verify_anchors(events: list, anchors: list, onchain_check, onchain_for=None) -> dict:
    """Compare the ledger with every anchor.

    events        all ledger events, sorted by seq
    anchors       dicts with from_seq, to_seq, event_count, head_hash,
                  merkle_root, digest, status, tx_id; sorted by to_seq.
                  Failed (never published) anchors must be left out.
    onchain_check callable(anchor) -> {"state": ..., "detail": ...} where
                  state is one of:
                    "confirmed"   on chain, right digest, right sender
                    "pending"     published, not final yet
                    "mismatch"    on chain but the digest or sender is wrong
                    "missing"     the transaction cannot be found
                    "unreachable" the chain could not be asked
    onchain_for   indexes (into `anchors`) to ask the chain about. The
                  default is the NEWEST anchor only - see below.

    Why asking the chain about just the newest anchor is enough: the
    chain check has already recomputed every event_hash, so an unchanged
    newest head_hash proves nothing before it moved. Older anchors are
    still checked locally (their stored digests are recomputed from the
    events), which catches tampering with the anchors table itself.

    Two kinds of outcome:
      problems    definite evidence of tampering or corruption
      unverified  could not be checked right now (chain unreachable,
                  transaction still pending) - NOT evidence of tampering
    """

    by_seq = {e.seq: i for i, e in enumerate(events)}
    seqs = [e.seq for e in events]

    problems = []
    unverified = []

    if onchain_for is None:
        onchain_for = {len(anchors) - 1} if anchors else set()

    previous_to = None

    for index, anchor in enumerate(anchors):
        label = f"anchor {anchor['from_seq']}-{anchor['to_seq']}"

        # --- coverage: no gaps, no overlaps between anchors ----------
        if previous_to is not None and anchor["from_seq"] <= previous_to:
            problems.append(f"{label}: overlaps the previous anchor")

        expected_first = None
        if previous_to is None:
            expected_first = seqs[0] if seqs else None
        else:
            expected_first = next((s for s in seqs if s > previous_to), None)

        if expected_first is not None and anchor["from_seq"] != expected_first:
            problems.append(
                f"{label}: events between the previous anchor and this one "
                "are not covered, or the first event of the batch is gone"
            )

        previous_to = anchor["to_seq"]

        # --- the newest event of the batch must still exist ----------
        head_pos = by_seq.get(anchor["to_seq"])

        if head_pos is None:
            problems.append(
                f"{label}: the event at seq {anchor['to_seq']} no longer "
                "exists (events were removed from the end of the ledger)"
            )
            continue

        if events[head_pos].event_hash != anchor["head_hash"]:
            problems.append(
                f"{label}: the event at seq {anchor['to_seq']} has a "
                "different hash than the one that was anchored "
                "(history was rewritten)"
            )
            continue

        # --- recompute the batch from the events as they are now -----
        in_batch = [e for e in events if anchor["from_seq"] <= e.seq <= anchor["to_seq"]]

        if len(in_batch) != anchor["event_count"]:
            problems.append(
                f"{label}: anchored {anchor['event_count']} events, "
                f"ledger now holds {len(in_batch)}"
            )
            continue

        recomputed_root = merkle_root([e.event_hash for e in in_batch])

        if recomputed_root != anchor["merkle_root"]:
            problems.append(f"{label}: Merkle root does not match the events")
            continue

        if anchor_digest(
            anchor["from_seq"], anchor["to_seq"],
            anchor["head_hash"], anchor["merkle_root"],
        ) != anchor["digest"]:
            problems.append(f"{label}: stored digest is inconsistent")
            continue

        # --- ask the public chain ------------------------------------
        if index in onchain_for:
            result = onchain_check(anchor)
            state = result.get("state")
            detail = result.get("detail", "")

            if state == "confirmed":
                pass
            elif state == "mismatch":
                problems.append(f"{label}: blockchain disagrees - {detail}")
            elif state == "missing" and anchor.get("status") == "confirmed":
                problems.append(
                    f"{label}: a transaction that was confirmed earlier "
                    f"cannot be found now - {detail}"
                )
            else:
                unverified.append(f"{label}: {state} - {detail}")

    unanchored = 0
    if events:
        last_to = anchors[-1]["to_seq"] if anchors else 0
        unanchored = sum(1 for e in events if e.seq > last_to)

    return {
        "ok": not problems,
        "anchors_checked": len(anchors),
        "onchain_checked": len([i for i in onchain_for if i < len(anchors)]),
        "problems": problems,
        "unverified": unverified,
        "unanchored_events": unanchored,
    }
