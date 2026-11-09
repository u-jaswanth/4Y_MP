"""
Tests for the Merkle tree, the anchor logic and the EVM provider.

No database and no internet needed:
    python tests/test_ledger_anchor.py

The EVM provider is exercised against a tiny fake JSON-RPC node that
runs on localhost. That tests the request/response handling and every
verdict check() can return. It does NOT test real signing or a real
chain - see the notes in the Phase 2/3 hand-over.
"""

import json
import os
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.ledger_hash import (  # noqa: E402
    GENESIS_HASH, canonical_payload, compute_event_hash, make_ref, sign_event,
    verify_chain, verify_event_signature,
)
from app.core.ledger_merkle import merkle_proof, merkle_root, verify_proof  # noqa: E402
from app.core.ledger_anchor import (  # noqa: E402
    anchor_digest, build_batch, onchain_payload, verify_anchors,
)
from app.core.ledger_providers import (  # noqa: E402
    EvmProvider, LocalFileProvider, AnchorProviderError, build_provider,
)

PASSED = 0
FAILED = 0


def check(name, condition):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ok    {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}")


# ---------------------------------------------------------------
# helpers
# ---------------------------------------------------------------

@dataclass
class Ev:
    seq: int
    request_id: str
    event_type: str
    patient_ref: str
    doctor_ref: str
    created_at: datetime
    prev_hash: str
    event_hash: str
    signature: str = None


def make_chain(n, start_seq=1, secret="s", gap_every=0):
    """A genuine chain of n events. gap_every>0 skips a seq now and then,
    like a rolled-back Postgres sequence value would."""
    events, prev, seq = [], GENESIS_HASH, start_seq
    base = datetime(2026, 1, 1, 12, 0, 0, 1)
    types = ["requested", "approved", "revoked"]
    for i in range(n):
        if gap_every and i and i % gap_every == 0:
            seq += 1
        rid = f"req-{i // 3}"
        p, d = make_ref(secret, "pat"), make_ref(secret, "doc")
        ts = base + timedelta(minutes=i)
        payload = canonical_payload(rid, types[i % 3], p, d, ts)
        h = compute_event_hash(prev, payload)
        events.append(Ev(seq, rid, types[i % 3], p, d, ts, prev, h))
        prev, seq = h, seq + 1
    return events


def rewrite_chain(events, edit):
    """What a database owner could do: change an event, then recompute
    every hash after it so the chain is perfectly self-consistent."""
    out, prev = [], GENESIS_HASH
    for e in events:
        new = Ev(**e.__dict__)
        edit(new)
        payload = canonical_payload(
            new.request_id, new.event_type, new.patient_ref, new.doctor_ref, new.created_at
        )
        new.prev_hash = prev
        new.event_hash = compute_event_hash(prev, payload)
        prev = new.event_hash
        out.append(new)
    return out


def anchors_for(events, sizes, provider=None, status="confirmed"):
    """Anchor the events in consecutive batches of the given sizes."""
    anchors, rest, n = [], list(events), 0
    for size in sizes:
        batch = build_batch(rest, max_events=size)
        n += 1
        batch["tx_id"] = provider.publish(batch["digest"])["tx_id"] if provider else f"tx{n}"
        batch["status"] = status
        anchors.append(batch)
        rest = [e for e in rest if e.seq > batch["to_seq"]]
    return anchors


def always(state, detail=""):
    return lambda anchor: {"state": state, "detail": detail}


# ---------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------

print("\nMerkle tree")

chain = make_chain(17)
hashes = [e.event_hash for e in chain]

all_ok = True
for size in range(1, 18):
    sub = hashes[:size]
    root = merkle_root(sub)
    for i in range(size):
        if not verify_proof(sub[i], merkle_proof(sub, i), root):
            all_ok = False
check("every event verifies against its root, for batch sizes 1..17", all_ok)

root = merkle_root(hashes[:8])
proof = merkle_proof(hashes[:8], 3)
check("a different event does not verify with someone else's proof",
      not verify_proof(hashes[4], proof, root))
check("a tampered proof step fails",
      not verify_proof(hashes[3], [dict(proof[0], hash="00" * 32)] + proof[1:], root))
check("a proof does not verify against a different root",
      not verify_proof(hashes[3], proof, merkle_root(hashes[:7])))
check("duplicating the last leaf gives a DIFFERENT root (no second-preimage trick)",
      merkle_root(hashes[:5]) != merkle_root(hashes[:5] + [hashes[4]]))
check("garbage proof input returns False, not an exception",
      verify_proof("zz", [{"side": "x"}], root) is False)

try:
    merkle_root([])
    check("empty batch is rejected", False)
except ValueError:
    check("empty batch is rejected", True)


# ---------------------------------------------------------------
# Anchor batches
# ---------------------------------------------------------------

print("\nBuilding anchors")

chain = make_chain(10)
batch = build_batch(chain)
check("a batch covers first..last seq and counts events",
      (batch["from_seq"], batch["to_seq"], batch["event_count"]) == (1, 10, 10))
check("head_hash is the newest event's hash", batch["head_hash"] == chain[-1].event_hash)
check("digest is reproducible",
      batch["digest"] == anchor_digest(1, 10, batch["head_hash"], batch["merkle_root"]))
check("max_events caps the batch", build_batch(chain, max_events=4)["to_seq"] == 4)
check("nothing to anchor -> None", build_batch([]) is None)
check("on-chain payload is magic + 32 bytes", len(onchain_payload(batch["digest"])) == 36)


# ---------------------------------------------------------------
# Verifying anchors: the happy path
# ---------------------------------------------------------------

print("\nVerifying anchors - healthy ledger")

chain = make_chain(12)
anchors = anchors_for(chain, [5, 4])          # covers seq 1-9; 10-12 not yet anchored
res = verify_anchors(chain, anchors, always("confirmed"))
check("healthy ledger passes", res["ok"] and not res["problems"])
check("counts events not yet anchored", res["unanchored_events"] == 3)
check("only the newest anchor is asked of the chain by default", res["onchain_checked"] == 1)

gappy = make_chain(12, gap_every=4)
res = verify_anchors(gappy, anchors_for(gappy, [5, 7]), always("confirmed"))
check("gaps in seq numbers (rolled-back inserts) are fine", res["ok"])

check("no anchors at all is fine", verify_anchors(chain, [], always("confirmed"))["ok"])


# ---------------------------------------------------------------
# The attacks Phase 1 could NOT catch
# ---------------------------------------------------------------

print("\nAttacks the chain alone could not catch")

chain = make_chain(12)
anchors = anchors_for(chain, [6, 6])

# Case C: change one old event, recompute every hash after it.
forged = rewrite_chain(chain, lambda e: setattr(e, "event_type", "denied") if e.seq == 2 else None)
check("(setup) the forged chain passes the Phase 1 chain check", verify_chain(forged)["ok"])
res = verify_anchors(forged, anchors, always("confirmed"))
check("CASE C - full rewrite with recomputed hashes is caught by the anchor",
      not res["ok"] and any("rewritten" in p for p in res["problems"]))

# Cutting events off the end.
cut = chain[:9]
check("(setup) the cut chain passes the Phase 1 chain check", verify_chain(cut)["ok"])
res = verify_anchors(cut, anchors, always("confirmed"))
check("TAIL CUT inside the anchored range is caught",
      not res["ok"] and any("no longer exists" in p for p in res["problems"]))

# Deleting a whole batch worth of recent events.
res = verify_anchors(chain[:6], anchors, always("confirmed"))
check("cutting back to the previous anchor is caught", not res["ok"])

# Honest limitation, asserted so it can't be forgotten.
anchors_first_only = anchors_for(chain, [6])          # events 7-12 are unanchored
res = verify_anchors(chain[:9], anchors_first_only, always("confirmed"))
check("LIMIT: cutting events written AFTER the newest anchor is NOT detected",
      res["ok"])

# Tampering with the anchors table itself.
bad = [dict(a) for a in anchors]
bad[0]["merkle_root"] = "ab" * 32
check("editing a stored Merkle root is caught",
      not verify_anchors(chain, bad, always("confirmed"))["ok"])

bad = [dict(a) for a in anchors]
bad[0]["digest"] = "cd" * 32
check("editing a stored digest is caught",
      not verify_anchors(chain, bad, always("confirmed"))["ok"])

bad = [dict(a) for a in anchors]
bad[0]["head_hash"] = chain[0].event_hash
check("editing a stored head hash is caught",
      not verify_anchors(chain, bad, always("confirmed"))["ok"])

# Coverage holes.
res = verify_anchors(chain, [anchors[1]], always("confirmed"))
check("an anchor that skips earlier events is caught", not res["ok"])

bad = [dict(a) for a in anchors]
bad[1]["from_seq"] = bad[0]["to_seq"]
check("overlapping anchors are caught",
      not verify_anchors(chain, bad, always("confirmed"))["ok"])

# Deleting an event in the middle of an anchored batch (trigger dropped).
holes = chain[:3] + chain[4:]
res = verify_anchors(holes, anchors, always("confirmed"))
check("deleting a middle event is caught", not res["ok"])


# ---------------------------------------------------------------
# What the blockchain can say
# ---------------------------------------------------------------

print("\nBlockchain verdicts")

chain = make_chain(8)
anchors = anchors_for(chain, [8])

res = verify_anchors(chain, anchors, always("mismatch", "wrong digest"))
check("on-chain MISMATCH is a problem", not res["ok"])

res = verify_anchors(chain, anchors, always("missing", "gone"))
check("missing tx on a CONFIRMED anchor is a problem", not res["ok"])

pending_anchor = [dict(anchors[0], status="pending")]
res = verify_anchors(chain, pending_anchor, always("missing", "not found yet"))
check("missing tx on a PENDING anchor is only 'unverified'",
      res["ok"] and len(res["unverified"]) == 1)

res = verify_anchors(chain, anchors, always("unreachable", "node down"))
check("an unreachable node is 'unverified', never a tamper alarm",
      res["ok"] and len(res["unverified"]) == 1)

res = verify_anchors(chain, anchors, always("pending", "3/12 confirmations"))
check("a pending tx is 'unverified', not a problem", res["ok"] and res["unverified"])


# ---------------------------------------------------------------
# Local provider
# ---------------------------------------------------------------

print("\nLocal file provider")

with tempfile.TemporaryDirectory() as tmp:
    provider = LocalFileProvider(os.path.join(tmp, "anchors.jsonl"))
    chain = make_chain(10)
    anchors = anchors_for(chain, [10], provider=provider)
    res = verify_anchors(chain, anchors, provider.check)
    check("publish then verify round-trips", res["ok"] and not res["unverified"])

    forged = rewrite_chain(chain, lambda e: setattr(e, "event_type", "denied") if e.seq == 1 else None)
    check("a rewrite is caught end-to-end with the local provider",
          not verify_anchors(forged, anchors, provider.check)["ok"])

    stolen = [dict(anchors[0], tx_id="local-99")]
    check("pointing the anchor at a transaction that isn't there is caught",
          not verify_anchors(chain, stolen, provider.check)["ok"])


# ---------------------------------------------------------------
# EVM provider against a fake JSON-RPC node
# ---------------------------------------------------------------

print("\nEVM provider (fake node)")

ME = "0x" + "11" * 20
THEM = "0x" + "22" * 20


class FakeNode:
    def __init__(self):
        self.txs = {}          # hash -> tx dict
        self.receipts = {}
        self.head = 1000
        self.sent = []
        self.fail_next = None


NODE = FakeNode()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        method, params = body["method"], body["params"]
        result, error = None, None

        if NODE.fail_next:
            error, NODE.fail_next = {"code": -32000, "message": NODE.fail_next}, None
        elif method == "eth_getTransactionCount":
            result = hex(7)
        elif method == "eth_maxPriorityFeePerGas":
            result = hex(30_000_000_000)
        elif method == "eth_getBlockByNumber":
            result = {"baseFeePerGas": hex(50_000_000_000)}
        elif method == "eth_estimateGas":
            result = hex(21_600)
        elif method == "eth_sendRawTransaction":
            NODE.sent.append(params[0])
            result = "0x" + "ab" * 32
        elif method == "eth_getTransactionByHash":
            result = NODE.txs.get(params[0])
        elif method == "eth_getTransactionReceipt":
            result = NODE.receipts.get(params[0])
        elif method == "eth_blockNumber":
            result = hex(NODE.head)
        else:
            error = {"code": -32601, "message": "unknown"}

        out = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result, "error": error})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out.encode())


server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{server.server_port}"

captured = {}


def fake_signer(tx):
    captured.update(tx)
    return "0xsigned"


evm = EvmProvider(URL, chain_id=80002, address=ME, confirmations=12, signer=fake_signer,
                  explorer_tx_url="https://explorer.example/tx")

digest = "ef" * 32
sent = evm.publish(digest)
check("publish returns the transaction hash, state pending",
      sent["tx_id"] == "0x" + "ab" * 32 and sent["state"] == "pending")
check("the transaction is zero-value, to ourselves, carrying CLG1 + digest",
      captured["value"] == 0 and captured["to"] == ME
      and captured["data"] == "0x" + onchain_payload(digest).hex())
check("nonce, chain id and fees were filled in",
      captured["nonce"] == 7 and captured["chainId"] == 80002
      and captured["maxFeePerGas"] == 50_000_000_000 * 2 + 30_000_000_000)
check("gas has headroom over the estimate", captured["gas"] > 21_600)
check("the signed payload is what gets sent", NODE.sent == ["0xsigned"])
check("explorer link is built", evm.explorer_url("0xabc") == "https://explorer.example/tx/0xabc")

anchor = {"tx_id": "0x" + "ab" * 32, "digest": digest, "status": "pending"}
good_data = "0x" + onchain_payload(digest).hex()


def put_tx(**over):
    tx = {"input": good_data, "from": ME, "blockNumber": hex(990)}
    tx.update(over)
    NODE.txs[anchor["tx_id"]] = tx
    NODE.receipts[anchor["tx_id"]] = {"status": "0x1"}


check("unknown tx -> missing", evm.check(anchor)["state"] == "missing")

put_tx(blockNumber=None)
check("tx in the mempool -> pending", evm.check(anchor)["state"] == "pending")

NODE.txs[anchor["tx_id"]]["blockNumber"] = hex(995)
NODE.head = 1000
r = evm.check(anchor)
check("too few confirmations -> pending", r["state"] == "pending" and "6/12" in r["detail"])

put_tx(blockNumber=hex(980))
r = evm.check(anchor)
check("enough confirmations -> confirmed", r["state"] == "confirmed" and r["block_number"] == 980)

put_tx(input="0x" + "00" * 36)
check("someone else's data in the tx -> mismatch", evm.check(anchor)["state"] == "mismatch")

put_tx(**{"from": THEM})
check("tx from a different sender -> mismatch (attacker's own tx doesn't count)",
      evm.check(anchor)["state"] == "mismatch")

put_tx()
NODE.receipts[anchor["tx_id"]] = {"status": "0x0"}
check("reverted tx -> mismatch", evm.check(anchor)["state"] == "mismatch")

put_tx()
NODE.fail_next = "rate limited"
check("node error -> unreachable (not mismatch)", evm.check(anchor)["state"] == "unreachable")

dead = EvmProvider("http://127.0.0.1:9", 1, ME, confirmations=1, timeout=2)
check("node down -> unreachable", dead.check(anchor)["state"] == "unreachable")

NODE.fail_next = "insufficient funds"
try:
    evm.publish(digest)
    check("a node error during publish raises AnchorProviderError", False)
except AnchorProviderError:
    check("a node error during publish raises AnchorProviderError", True)

keyless = EvmProvider(URL, 1, ME)
try:
    keyless.publish(digest)
    check("publishing without a key is refused", False)
except AnchorProviderError:
    check("publishing without a key is refused", True)

# whole flow: publish -> confirm -> rewrite attempt
chain = make_chain(6)
batch = build_batch(chain)
batch["tx_id"], batch["status"] = anchor["tx_id"], "confirmed"
put_tx(input="0x" + onchain_payload(batch["digest"]).hex(), blockNumber=hex(900))
check("end to end: healthy chain verifies against the fake node",
      verify_anchors(chain, [batch], evm.check)["ok"])
forged = rewrite_chain(chain, lambda e: setattr(e, "event_type", "denied") if e.seq == 1 else None)
check("end to end: a full rewrite is caught",
      not verify_anchors(forged, [batch], evm.check)["ok"])

# Rewrite AND re-point the anchor row at attacker's transaction on THEIR address
fake_digest_batch = build_batch(forged)
fake_digest_batch["tx_id"], fake_digest_batch["status"] = "0x" + "cd" * 32, "confirmed"
NODE.txs[fake_digest_batch["tx_id"]] = {
    "input": "0x" + onchain_payload(fake_digest_batch["digest"]).hex(),
    "from": THEM, "blockNumber": hex(900),
}
NODE.receipts[fake_digest_batch["tx_id"]] = {"status": "0x1"}
check("end to end: rewrite + a matching tx from the attacker's own address is caught",
      not verify_anchors(forged, [fake_digest_batch], evm.check)["ok"])

# configuration
try:
    build_provider({"provider": "evm"})
    check("incomplete EVM config is rejected", False)
except AnchorProviderError:
    check("incomplete EVM config is rejected", True)
check("provider 'none' builds a disabled provider", not build_provider({"provider": "none"}).enabled)

server.shutdown()

# ---------------------------------------------------------------
# Event signatures (HMAC) - the "attacker INSERTs a valid-hash event" gap
# ---------------------------------------------------------------

print("\nEvent signatures")

import types  # noqa: E402
import uuid  # noqa: E402

SECRET = "test-ledger-secret"

# record_event() is the function every consent route calls. It needs
# SQLAlchemy models, which this no-database test does not use, so the
# few modules it imports from are replaced with stand-ins and it runs
# against a tiny fake session.
class FakeConsentEvent:
    seq = types.SimpleNamespace(desc=lambda: None)

    def __init__(self, **fields):
        self.__dict__.update(fields)


class FakeSession:
    def __init__(self):
        self.rows = []

    def get_bind(self):
        return types.SimpleNamespace(dialect=types.SimpleNamespace(name="sqlite"))

    def query(self, _model):
        return self

    def order_by(self, _clause):
        return self

    def first(self):
        return self.rows[-1] if self.rows else None

    def add(self, row):
        self._pending = row

    def flush(self):
        self._pending.seq = len(self.rows) + 1
        self.rows.append(self._pending)


def _stub(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module


_stub("app.config", LEDGER_HMAC_SECRET=SECRET)
_stub("app.models", __path__=[])
_stub("app.models.access_request", AccessRequest=object)
_stub("app.models.consent_event", ConsentEvent=FakeConsentEvent)
try:
    import sqlalchemy  # noqa: F401
except ImportError:
    _stub("sqlalchemy", text=lambda sql: sql)
    _stub("sqlalchemy.orm", Session=object)

from app.core.ledger import record_event  # noqa: E402

db = FakeSession()
req = types.SimpleNamespace(id=uuid.uuid4(), patient_id=uuid.uuid4(), doctor_id=uuid.uuid4())
for kind in ("requested", "approved", "revoked"):
    record_event(db, req, kind)           # same call the FastAPI routes make

legit = db.rows
check("legitimate events are written with a signature",
      len(legit) == 3 and all(e.signature for e in legit))
check("each legitimate signature is valid",
      all(verify_event_signature(SECRET, e.event_hash, e.signature) for e in legit))
res = verify_chain(legit, SECRET)
check("a chain of legitimate events verifies, signatures included",
      res["ok"] and res["signatures_verified"] and res["signed"] == 3
      and res["legacy_unsigned"] == 0)

# The attack: after requested -> approved -> revoked, insert a fake
# "approved" with a correctly computed hash chained onto the last event.
def forge(after, signature):
    ts = datetime(2026, 6, 1, 12, 0, 0, 1)
    payload = canonical_payload(
        after.request_id, "approved", after.patient_ref, after.doctor_ref, ts)
    return FakeConsentEvent(
        seq=after.seq + 1, request_id=after.request_id, event_type="approved",
        patient_ref=after.patient_ref, doctor_ref=after.doctor_ref, created_at=ts,
        prev_hash=after.event_hash,
        event_hash=compute_event_hash(after.event_hash, payload),
        signature=signature)

fake = forge(legit[-1], None)
check("(setup) the forged event passes the hash chain check on its own",
      verify_chain(legit + [fake])["ok"])
res = verify_chain(legit + [fake], SECRET)
check("FORGED event with no signature is caught and identified",
      not res["ok"] and res["broken_at_seq"] == 4
      and res["event_hash"] == fake.event_hash and res["request_id"] == str(req.id))

for label, sig in (
    ("signed with the wrong secret", sign_event("attacker-guess", forge(legit[-1], None).event_hash)),
    ("empty signature", ""),
    ("garbage signature", "zz" * 32),
    ("signature copied from another event", legit[0].signature),
):
    res = verify_chain(legit + [forge(legit[-1], sig)], SECRET)
    check(f"FORGED event ({label}) is caught", not res["ok"] and res["broken_at_seq"] == 4)

# A legitimate event written after the forgery chains onto it, but the
# forged one is still the one reported.
later = FakeConsentEvent(**{**fake.__dict__, "seq": 5, "prev_hash": fake.event_hash,
                           "event_type": "revoked"})
later.event_hash = compute_event_hash(
    fake.event_hash,
    canonical_payload(later.request_id, "revoked", later.patient_ref, later.doctor_ref, later.created_at))
later.signature = sign_event(SECRET, later.event_hash)
res = verify_chain(legit + [fake, later], SECRET)
check("the forged event is still the one reported when real events follow it",
      not res["ok"] and res["broken_at_seq"] == 4)

# Legacy (pre-signing) events: explicit, not silently signed.
old_style = [FakeConsentEvent(**{**e.__dict__, "signature": None}) for e in make_chain(4)]
res = verify_chain(old_style, SECRET)
check("old unsigned events are accepted as legacy and counted",
      res["ok"] and res["legacy_unsigned"] == 4 and res["signed"] == 0)

last_old = old_style[-1]
new_ts = datetime(2026, 7, 1, 0, 0, 0, 1)
new_hash = compute_event_hash(
    last_old.event_hash,
    canonical_payload("req-9", "requested", last_old.patient_ref, last_old.doctor_ref, new_ts))
signed_after_legacy = FakeConsentEvent(
    seq=last_old.seq + 1, request_id="req-9", event_type="requested",
    patient_ref=last_old.patient_ref, doctor_ref=last_old.doctor_ref, created_at=new_ts,
    prev_hash=last_old.event_hash, event_hash=new_hash,
    signature=sign_event(SECRET, new_hash))
res = verify_chain(old_style + [signed_after_legacy], SECRET)
check("legacy events followed by signed events verify",
      res["ok"] and res["legacy_unsigned"] == 4 and res["signed"] == 1)

unsigned_forgery = forge(signed_after_legacy, None)
res = verify_chain(old_style + [signed_after_legacy, unsigned_forgery], SECRET)
check("an UNSIGNED event after signing began is forgery, not 'legacy'",
      not res["ok"] and res["broken_at_seq"] == unsigned_forgery.seq)

check("without a secret the signature check is skipped, and says so",
      verify_chain(legit + [fake])["signatures_verified"] is False)


print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
