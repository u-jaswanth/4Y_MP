# Consent ledger - Phases 2 and 3

## What runs
A background thread starts with the API. Every LEDGER_CHECK_INTERVAL_MINUTES (15) it:
1. confirms pending anchors / republishes lost ones,
2. publishes a new anchor if events were written since the last one and the
   anchor interval (60 min) has passed,
3. checks the chain, reconciles against access_requests, verifies anchors
   against the blockchain, saves the result, and alerts if something is wrong.

## .env - try it first with no blockchain
    LEDGER_ANCHOR_PROVIDER=local        # file on this machine; development only

## .env - real anchoring (use a TESTNET first)
    LEDGER_ANCHOR_PROVIDER=evm
    LEDGER_EVM_RPC_URL=https://...                 # from your RPC provider
    LEDGER_EVM_CHAIN_ID=...                        # of the chain you chose
    LEDGER_EVM_PRIVATE_KEY=0x...                   # a wallet made ONLY for this
    LEDGER_EVM_ADDRESS=0x...                       # optional if eth-account is installed
    LEDGER_EVM_CONFIRMATIONS=12
    LEDGER_EXPLORER_TX_URL=https://<explorer>/tx   # makes receipts clickable
    LEDGER_ALERT_WEBHOOK_URL=https://hooks.slack.com/...   # optional

    pip install eth-account

Fund the wallet with a small amount of that chain's coin. Each anchor is one
tiny transaction.

## Event signatures
Every event written by the API carries an HMAC-SHA256 signature (made with
LEDGER_HMAC_SECRET) in `consent_events.signature`. /admin/ledger/verify and
the scheduled check verify it; an event inserted straight into Postgres has
no valid signature, so the ledger reports unhealthy and names its `seq`.

- The column is added automatically at startup (nullable).
- Events from before this change keep `signature = NULL` and are reported as
  "legacy" (a warning, not a failure). They are accepted only as an unbroken
  prefix: once a signed event exists, a later unsigned event counts as forged.
- Changing LEDGER_HMAC_SECRET invalidates every signature (and every
  patient/doctor ref). Treat it as a permanent secret; keep it out of the DB.

## Admin endpoints
    GET  /admin/ledger/verify[?full=true]   check everything now
    GET  /admin/ledger/status               last scheduled check + recent anchors
    POST /admin/ledger/anchor               publish an anchor now

## Patient endpoints
    GET /access/history                     events now carry `anchor` (when covered)
    GET /access/receipt/{event_hash}        Merkle proof + blockchain transaction

## Tests (no database or internet needed)
    python tests/test_ledger_anchor.py
