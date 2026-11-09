from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


class LedgerAnchor(Base):
    """One digest published to a public chain, covering a run of events.

    Unlike consent_events this table is NOT append-only: an anchor
    starts "pending" and becomes "confirmed" once the transaction is
    deep enough in the chain. Nothing here is trusted on its own - every
    check recomputes the digest from the events and compares it with
    what is actually on the chain (see app/core/ledger_anchor.py).
    """

    __tablename__ = "ledger_anchors"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # The batch: every event with from_seq <= seq <= to_seq.
    from_seq = Column(BigInteger, nullable=False)
    to_seq = Column(BigInteger, nullable=False, index=True)
    event_count = Column(Integer, nullable=False)

    head_hash = Column(String(64), nullable=False)
    merkle_root = Column(String(64), nullable=False)
    digest = Column(String(64), nullable=False)

    provider = Column(String, nullable=False)
    tx_id = Column(String, nullable=True)

    # pending | confirmed
    status = Column(String, nullable=False, default="pending")
    block_number = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    # e.g. "previous tx 0x... was never mined; republished"
    last_error = Column(Text, nullable=True)


class LedgerCheck(Base):
    """Result of one scheduled integrity check - a small history so an
    admin can see when things were last healthy. Pruned automatically."""

    __tablename__ = "ledger_checks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ran_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    healthy = Column(Boolean, nullable=False)
    summary = Column(Text, nullable=False)  # JSON
