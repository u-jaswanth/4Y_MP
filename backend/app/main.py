from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_ORIGIN
from app.vectorstore.bootstrap import ensure_pgvector_extension
from app.core.db_migrations import (
    ensure_report_summary_columns,
    ensure_hospital_table,
    ensure_doctor_table,
    ensure_portal_columns,
    ensure_patient_columns,
    ensure_access_tables,
    ensure_ledger_table,
    ensure_ledger_anchor_tables,
)
from app.core.bootstrap_admin import ensure_admin_account
from app.core.ledger_anchoring import start_worker, stop_worker

from app.auth.routes import router as auth_router
from app.reports.routes import router as reports_router
from app.chat.routes import router as chat_router
from app.doctors.routes import router as doctors_router

# Portals
from app.admin.routes import router as admin_router
from app.hospitals.routes import router as hospital_router
from app.doctors.portal import router as doctor_portal_router
from app.doctors.patient_access import router as doctor_patient_access_router
from app.access.routes import router as access_router
from app.ledger_routes import router as ledger_router


app = FastAPI(title="MediConnect AI API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_ORIGIN,
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

app.include_router(auth_router)
app.include_router(reports_router)
app.include_router(chat_router)
app.include_router(doctors_router)

# /admin      - the one admin issues hospital accounts
# /hospital   - a hospital adds and removes its own doctors
# /doctor     - a doctor reads their own profile
app.include_router(admin_router)
app.include_router(hospital_router)
app.include_router(doctor_portal_router)

# /doctor patient-access routes (find patient, send request, my
# patients, patient record, ask about patient) and /access (the
# patient's side: approve / deny / revoke).
app.include_router(doctor_patient_access_router)
app.include_router(access_router)

# /admin/ledger - integrity checks on the consent ledger
app.include_router(ledger_router)


# ---------------------------------------------------------
# Startup
# ---------------------------------------------------------

@app.on_event("startup")
def on_startup():
    # Make sure pgvector extension exists
    ensure_pgvector_extension()

    # Make sure report summary columns exist
    ensure_report_summary_columns()

    # Make sure the Health ID column exists
    ensure_patient_columns()

    # Hospitals first: doctors.hospital_id points at it.
    ensure_hospital_table()
    ensure_doctor_table()

    # Then the columns that the portals added to the tables that
    # already existed before them (users, doctors).
    ensure_portal_columns()

    # The doctor <-> patient access-request flow and the doctor's
    # per-patient chat log. Both point at doctors/patients, so this
    # runs after the tables above exist.
    ensure_access_tables()

    # The tamper-evident consent ledger. Has no foreign keys, so order
    # does not matter, but it is only useful after access_requests.
    ensure_ledger_table()

    # Anchors (blockchain) and the log of scheduled checks.
    ensure_ledger_anchor_tables()

    # Exactly one admin, created only if there isn't one already.
    # See app/core/bootstrap_admin.py - this never resets an existing
    # admin's password.
    ensure_admin_account()

    # Scheduled integrity checks and (if configured) blockchain anchors.
    start_worker()


@app.on_event("shutdown")
def on_shutdown():
    stop_worker()


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "MediConnect AI API",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
