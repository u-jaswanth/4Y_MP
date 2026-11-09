from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.vectorstore.models import DocumentChunkRecord


class PgVectorStore:
    """
    Postgres + pgvector replacement for the old
    `ChromaVectorStore` (backend/data/chroma/, collection
    "medical_documents").

    Keeps the same three-method interface (add_chunk / get_document /
    count) so app/ingestion_pipeline.py and
    app/retrieval/rag_retriever.py didn't need to change how they
    call it.
    """

    def add_chunk(
        self,
        chunk_id: str,
        content: str,
        embedding: list[float],
        metadata: dict,
    ):
        db = SessionLocal()

        try:
            stmt = pg_insert(DocumentChunkRecord).values(
                id=chunk_id,
                document_id=metadata.get("document_id", chunk_id),
                content=content,
                embedding=embedding,
                chunk_metadata=metadata,
            )

            stmt = stmt.on_conflict_do_update(
                index_elements=[DocumentChunkRecord.id],
                set_={
                    "document_id": stmt.excluded.document_id,
                    "content": stmt.excluded.content,
                    "embedding": stmt.excluded.embedding,
                    "chunk_metadata": stmt.excluded.chunk_metadata,
                },
            )

            db.execute(stmt)
            db.commit()

        finally:
            db.close()

    def get_document(self, document_id: str):
        db = SessionLocal()

        try:
            record = (
                db.query(DocumentChunkRecord)
                .filter(DocumentChunkRecord.document_id == document_id)
                .first()
            )

            if not record:
                return None

            return {
                "chunk_id": record.id,
                "content": record.content,
                "metadata": record.chunk_metadata,
            }

        finally:
            db.close()

    def count(self) -> int:
        db = SessionLocal()

        try:
            return db.query(DocumentChunkRecord).count()

        finally:
            db.close()
