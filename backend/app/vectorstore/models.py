"""
SQLAlchemy models for the pgvector-backed vector store.

These replace the three Chroma collections the project used to
keep in ``backend/data/chroma/``:

    medical_documents   -> DocumentChunkRecord  (vector_document_chunks)
    medical_observations-> ObservationRecord    (vector_observations)
    medical_knowledge   -> KnowledgeChunkRecord  (vector_knowledge_chunks)

Everything now lives in the same Postgres database as the rest of
the app (users/patients/reports), using the `vector` extension from
pgvector. Run:

    CREATE EXTENSION IF NOT EXISTS vector;

once against your database (see SETUP_GUIDE.md) before running
`alembic upgrade head`, since the `vector` column type only exists
once the extension is installed.

EMBEDDING_DIM matches BAAI/bge-m3 (see app/embeddings/embedder.py),
which produces 1024-dimensional embeddings.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base

EMBEDDING_DIM = 1024


class DocumentChunkRecord(Base):
    """One row per ingested report (one RAG chunk per document)."""

    __tablename__ = "vector_document_chunks"

    id = Column(String, primary_key=True)  # chunk_id
    document_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    chunk_metadata = Column(JSONB, nullable=False, default=dict)


class ObservationRecord(Base):
    """One row per individual lab observation extracted from a report."""

    __tablename__ = "vector_observations"

    id = Column(String, primary_key=True)  # observation_id
    document_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    observation_name = Column(String, nullable=True)
    canonical_name = Column(String, nullable=True)
    aliases = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    section_type = Column(String, nullable=True)


class KnowledgeChunkRecord(Base):
    """One row per chunk of the general medical knowledge base."""

    __tablename__ = "vector_knowledge_chunks"

    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    title = Column(String, nullable=True)
    source = Column(String, nullable=True)
    knowledge_type = Column(String, nullable=True)
