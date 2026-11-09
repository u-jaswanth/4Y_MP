from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ConsentEvent(Base):
    """One entry in the tamper-evident consent ledger.

    APPEND-ONLY. The application only ever INSERTs into this table;
    a Postgres trigger (see ensure_ledger_table in
    app/core/db_migrations.py) also rejects UPDATE, DELETE and
    TRUNCATE.

    access_requests keeps only the LATEST status of a request. This
    table keeps every step - requested, approved, revoked, approved
    again... - each one chained to the one before it by hash.

    Nothing identifying is stored: patient_ref / doctor_ref are keyed
    hashes (HMAC) of the real IDs, and there is no name, note or report
    content. request_id is deliberately NOT a foreign key, so the
    ledger never blocks (or is changed by) anything done to
    access_requests.
    """

    __tablename__ = "consent_events"

    # Strict order of events. Inserts are serialised by an advisory
    # lock in app/core/ledger.py, so seq order == chain order.
    seq = Column(BigInteger, primary_key=True, autoincrement=True)

    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # requested | approved | denied | revoked
    event_type = Column(String, nullable=False)

    patient_ref = Column(String(64), nullable=False)
    doctor_ref = Column(String(64), nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    prev_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, unique=True)

    # HMAC-SHA256 of event_hash, made with LEDGER_HMAC_SECRET by the
    # application (app/core/ledger.py). Proves the application wrote
    # the event: the hash alone can be computed by anyone with database
    # access. NULL = written before signing existed ("legacy") - the
    # verifier only accepts NULL for such an unbroken early prefix.
    signature = Column(String(64), nullable=True)

    # Phase 3: filled in once this event is covered by a blockchain
    # anchor. Unused (always NULL) in Phase 1.
    batch_id = Column(String, nullable=True)
