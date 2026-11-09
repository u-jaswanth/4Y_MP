import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.report import ReportOut


# ============================================================
# REQUESTING ACCESS (doctor -> patient)
# ============================================================

class AccessRequestCreate(BaseModel):
    health_id: str
    note: Optional[str] = Field(default=None, max_length=500)


class DoctorBrief(BaseModel):
    """Just enough about the doctor for the patient to decide."""

    id: uuid.UUID
    full_name: str
    specialty: str
    hospital: Optional[str] = None
    login_id: Optional[str] = None

    class Config:
        from_attributes = True


class PatientBrief(BaseModel):
    """Just enough about the patient for a doctor to confirm identity
    before sending a request, and to head a patient record screen."""

    id: uuid.UUID
    full_name: str
    health_id: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None

    class Config:
        from_attributes = True


class PatientLookupOut(PatientBrief):
    """What a doctor sees after typing a Health ID into Find patient -
    the patient's identity plus whatever the doctor's relationship to
    them already is, so the button reads correctly ("Send request" vs
    "Request pending" vs "You already have access")."""

    access_status: Optional[str] = None  # None | pending | approved | denied | revoked


class AccessRequestOut(BaseModel):
    id: uuid.UUID
    status: str
    note: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None
    doctor: Optional[DoctorBrief] = None
    patient: Optional[PatientBrief] = None

    class Config:
        from_attributes = True


class AnchorBrief(BaseModel):
    """Whether (and where) an event is covered by a blockchain anchor.

    Absent on an event means it has not been anchored YET - anchors are
    published on a schedule, so the newest events wait a little.
    """

    status: str  # pending | confirmed
    provider: str
    tx_id: Optional[str] = None
    explorer_url: Optional[str] = None
    published_at: Optional[datetime] = None


class ConsentEventOut(BaseModel):
    """One step in a request's history, as recorded in the ledger.

    The hashes are included so the patient can keep them as a receipt
    and check them against the blockchain anchor (see /access/receipt).
    """

    seq: int
    event_type: str
    created_at: datetime
    prev_hash: str
    event_hash: str
    anchor: Optional[AnchorBrief] = None

    class Config:
        from_attributes = True


class MerkleStep(BaseModel):
    side: str  # where the sibling sits: "left" | "right"
    hash: str


class ReceiptOut(BaseModel):
    """Everything needed to check one event without trusting this server.

    To verify: start from `event_hash`, combine it with each step of
    `proof` in order (see app/core/ledger_merkle.py for the exact
    hashing) and you must arrive at `merkle_root`; then
    SHA-256("consent-ledger-anchor-v1|from|to|head_hash|merkle_root")
    must equal `digest`, and the blockchain transaction `tx_id` must
    carry that digest.
    """

    event_hash: str
    event_type: str
    created_at: datetime
    anchored: bool
    status: Optional[str] = None
    detail: Optional[str] = None
    provider: Optional[str] = None
    tx_id: Optional[str] = None
    explorer_url: Optional[str] = None
    from_seq: Optional[int] = None
    to_seq: Optional[int] = None
    head_hash: Optional[str] = None
    merkle_root: Optional[str] = None
    digest: Optional[str] = None
    proof: list[MerkleStep] = Field(default_factory=list)
    proof_valid: Optional[bool] = None


class ConsentHistoryItem(BaseModel):
    """One request and every step the ledger recorded for it - what the
    patient's "Consent history" list shows, including requests that are
    no longer pending or active (denied, revoked)."""

    request_id: uuid.UUID
    status: str
    created_at: datetime
    doctor: Optional[DoctorBrief] = None
    events: list[ConsentEventOut] = Field(default_factory=list)


class AccessRequestsOut(BaseModel):
    """The patient's Doctor access page: what's waiting on them, and
    what's already granted."""

    pending: list[AccessRequestOut] = Field(default_factory=list)
    active: list[AccessRequestOut] = Field(default_factory=list)


# ============================================================
# THE PATIENT RECORD, AS A DOCTOR WITH APPROVED ACCESS SEES IT
# ============================================================

class PatientRecordOut(BaseModel):
    patient: PatientBrief
    access: AccessRequestOut

    clinical_summary: str
    observation_count: int = 0
    reports_analyzed: int = 0
    summary_generated_at: Optional[datetime] = None

    reports: list[ReportOut] = Field(default_factory=list)


# ============================================================
# "ASK ABOUT THIS PATIENT" (doctor-side chatbot)
# ============================================================

class DoctorChatRequest(BaseModel):
    message: str


class DoctorChatResponse(BaseModel):
    answer: str
    scope: str
    patient_observations_used: int
    knowledge_chunks_used: int


class DoctorChatHistoryTurn(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class DoctorChatHistoryOut(BaseModel):
    messages: list[DoctorChatHistoryTurn]
