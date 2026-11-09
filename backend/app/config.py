import os

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/mediconnect"
)


# ============================================================
# AUTH / JWT
# ============================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-secret-in-production"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)


# ============================================================
# ADMIN ACCOUNT
# ============================================================
#
# There is no admin sign-up page and no endpoint that creates an admin.
# The single admin account is created at startup from these two values
# (see app/core/bootstrap_admin.py), and only when no admin exists yet.
#
# Changing ADMIN_PASSWORD here does NOT change the password of a
# database that already has an admin in it. Sign in and use
# POST /auth/change-password for that.

ADMIN_EMAIL = os.getenv(
    "ADMIN_EMAIL",
    "admin@mediconnect.ai"
)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


# ============================================================
# CORS
# ============================================================

FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173"
)


# ============================================================
# CONSENT LEDGER
# ============================================================
#
# Secret key used to turn patient / doctor IDs into the opaque
# fingerprints stored in the consent ledger (see app/core/ledger.py).
# Without it, nobody can match a ledger entry to a person.
#
# Generate one with:
#   python -c "import secrets; print(secrets.token_hex(32))"
#
# Keep it separate from JWT_SECRET_KEY and never commit it. Changing it
# later does NOT break existing ledger entries (verification doesn't use
# it); it only changes the fingerprints of NEW entries.

LEDGER_HMAC_SECRET = os.getenv(
    "LEDGER_HMAC_SECRET",
    "dev-only-ledger-secret-change-me"
)

if LEDGER_HMAC_SECRET == "dev-only-ledger-secret-change-me":
    print(
        "[ledger] WARNING: LEDGER_HMAC_SECRET is not set - using the "
        "development default. Set a real one before using real data."
    )


# ------------------------------------------------------------
# Phase 2: scheduled integrity checks
# ------------------------------------------------------------
#
# A background thread inside the API process verifies the ledger every
# LEDGER_CHECK_INTERVAL_MINUTES, stores the result (GET
# /admin/ledger/status) and, if LEDGER_ALERT_WEBHOOK_URL is set, posts
# a Slack-style {"text": ...} message when something is wrong. Several
# API workers are fine: a database lock makes only one of them run
# each round.

LEDGER_WORKER_ENABLED = os.getenv("LEDGER_WORKER_ENABLED", "true").lower() == "true"

LEDGER_CHECK_INTERVAL_MINUTES = int(os.getenv("LEDGER_CHECK_INTERVAL_MINUTES", "15"))

LEDGER_ALERT_WEBHOOK_URL = os.getenv("LEDGER_ALERT_WEBHOOK_URL")

# While a problem persists, repeat the alert at most this often.
LEDGER_ALERT_REPEAT_MINUTES = int(os.getenv("LEDGER_ALERT_REPEAT_MINUTES", "360"))


# ------------------------------------------------------------
# Phase 3: blockchain anchor
# ------------------------------------------------------------
#
# LEDGER_ANCHOR_PROVIDER:
#   none   no anchoring (default). Checks still run.
#   local  writes anchors to a file - for trying it out on a laptop
#          only; proves nothing against someone who controls the server.
#   evm    publishes to an Ethereum-compatible chain (Polygon, Ethereum,
#          Base, ...). Start on a TESTNET.
#
# For evm you need an RPC URL, the chain id, and a wallet that holds a
# little of that chain's coin to pay fees. Use a wallet created ONLY for
# this - it never needs to hold anything else. Its address is pinned
# here, not in the database: anchors sent from any other address are
# rejected, so someone who rewrites the database cannot point it at
# their own transaction.
#
#   pip install eth-account       (needed to sign; not needed to verify)

LEDGER_ANCHOR_PROVIDER = os.getenv("LEDGER_ANCHOR_PROVIDER", "none")

# How often a new anchor is published, if there are new events.
LEDGER_ANCHOR_INTERVAL_MINUTES = int(os.getenv("LEDGER_ANCHOR_INTERVAL_MINUTES", "60"))

# Largest number of events covered by one anchor.
LEDGER_ANCHOR_MAX_EVENTS = int(os.getenv("LEDGER_ANCHOR_MAX_EVENTS", "5000"))

# A pending transaction that the node still cannot find after this long
# is published again.
LEDGER_ANCHOR_STUCK_MINUTES = int(os.getenv("LEDGER_ANCHOR_STUCK_MINUTES", "120"))

LEDGER_LOCAL_ANCHOR_FILE = os.getenv("LEDGER_LOCAL_ANCHOR_FILE", "ledger_anchors.jsonl")

LEDGER_EVM_RPC_URL = os.getenv("LEDGER_EVM_RPC_URL")
LEDGER_EVM_CHAIN_ID = os.getenv("LEDGER_EVM_CHAIN_ID")
LEDGER_EVM_PRIVATE_KEY = os.getenv("LEDGER_EVM_PRIVATE_KEY")
LEDGER_EVM_ADDRESS = os.getenv("LEDGER_EVM_ADDRESS")
LEDGER_EVM_CONFIRMATIONS = os.getenv("LEDGER_EVM_CONFIRMATIONS", "12")

# Base of a block-explorer transaction link, e.g.
# https://<explorer>/tx  - the transaction hash is appended.
LEDGER_EXPLORER_TX_URL = os.getenv("LEDGER_EXPLORER_TX_URL")

LEDGER_ANCHOR_CONFIG = {
    "provider": LEDGER_ANCHOR_PROVIDER,
    "local_path": LEDGER_LOCAL_ANCHOR_FILE,
    "evm_rpc_url": LEDGER_EVM_RPC_URL,
    "evm_chain_id": LEDGER_EVM_CHAIN_ID,
    "evm_private_key": LEDGER_EVM_PRIVATE_KEY,
    "evm_address": LEDGER_EVM_ADDRESS,
    "evm_confirmations": LEDGER_EVM_CONFIRMATIONS,
    "explorer_tx_url": LEDGER_EXPLORER_TX_URL,
}


# ============================================================
# FILE UPLOADS
# ============================================================

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
REPORTS_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "reports")
AADHAAR_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "aadhaar")


# ============================================================
# CLOUDINARY (optional off-site file storage)
# ============================================================
#
# When these are set, uploaded reports and Aadhaar photos are
# additionally mirrored to Cloudinary and their secure_url /
# public_id are stored alongside the local copy (which the RAG
# pipeline still reads from disk). If they are NOT set, the app
# behaves exactly like before - local disk storage only - so
# Cloudinary is a purely additive, optional feature.

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

CLOUDINARY_ENABLED = bool(
    CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET
)


# ============================================================
# GEMINI / RAG (used by app.understanding.llm and
# app.generation.answer_generator)
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

# NOTE: we only hard-fail on a missing Gemini key when the
# RAG/chat pipeline is actually used (see app/chat/routes.py),
# not at import time - otherwise auth/reports endpoints would
# break if GEMINI_API_KEY is not set yet.
