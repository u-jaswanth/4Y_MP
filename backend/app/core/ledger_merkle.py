"""
Merkle tree over a batch of ledger event hashes - no database, no network.

Why a tree on top of the chain? The chain already commits to all of
history through its newest hash. The tree adds one thing: a SHORT PROOF
that one particular event is inside an anchored batch, which a patient
can check without downloading everyone else's events.

Details that matter for safety:
  * leaves and inner nodes are hashed with different prefixes (0x00 /
    0x01), so an inner node can never be passed off as a leaf;
  * a node with no partner is carried up unchanged (no duplicating the
    last leaf, which is the classic way two different batches end up
    with one root).
"""

import hashlib


def _leaf(event_hash: str) -> bytes:
    return hashlib.sha256(b"\x00" + bytes.fromhex(event_hash)).digest()


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _levels(event_hashes: list) -> list:
    if not event_hashes:
        raise ValueError("cannot build a Merkle tree from zero events")

    level = [_leaf(h) for h in event_hashes]
    levels = [level]

    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                nxt.append(_node(level[i], level[i + 1]))
            else:
                nxt.append(level[i])  # unpaired: carried up as is
        level = nxt
        levels.append(level)

    return levels


def merkle_root(event_hashes: list) -> str:
    """Hex root of the tree. `event_hashes` must be in seq order."""

    return _levels(event_hashes)[-1][0].hex()


def merkle_proof(event_hashes: list, index: int) -> list:
    """The steps needed to prove event_hashes[index] is under the root.

    Returns [{"side": "left"|"right", "hash": hex}, ...] - "side" is
    where the SIBLING sits relative to the running value.
    """

    if not 0 <= index < len(event_hashes):
        raise IndexError("event index outside the batch")

    levels = _levels(event_hashes)
    proof = []
    position = index

    for level in levels[:-1]:
        if position % 2 == 0:
            if position + 1 < len(level):
                proof.append({"side": "right", "hash": level[position + 1].hex()})
            # else: unpaired, nothing to add at this level
        else:
            proof.append({"side": "left", "hash": level[position - 1].hex()})
        position //= 2

    return proof


def verify_proof(event_hash: str, proof: list, root: str) -> bool:
    """True if `event_hash` plus `proof` rebuilds exactly `root`."""

    try:
        running = _leaf(event_hash)

        for step in proof:
            sibling = bytes.fromhex(step["hash"])
            if step["side"] == "left":
                running = _node(sibling, running)
            elif step["side"] == "right":
                running = _node(running, sibling)
            else:
                return False

        return running.hex() == root

    except (ValueError, KeyError, TypeError):
        return False
