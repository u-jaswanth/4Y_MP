from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.vectorstore.models import KnowledgeChunkRecord


class MedicalKnowledgeStore:
    """
    General medical knowledge base (e.g. MedRAG textbook chunks),
    now backed by Postgres/pgvector instead of a local Chroma
    collection ("medical_knowledge").
    """

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):

        if not chunks:
            return

        db = SessionLocal()

        try:
            for chunk, embedding in zip(chunks, embeddings):

                stmt = pg_insert(KnowledgeChunkRecord).values(
                    id=chunk["chunk_id"],
                    content=chunk["content"],
                    embedding=embedding,
                    title=chunk.get("title"),
                    source=chunk.get("source"),
                    knowledge_type=chunk.get("knowledge_type"),
                )

                stmt = stmt.on_conflict_do_update(
                    index_elements=[KnowledgeChunkRecord.id],
                    set_={
                        "content": stmt.excluded.content,
                        "embedding": stmt.excluded.embedding,
                        "title": stmt.excluded.title,
                        "source": stmt.excluded.source,
                        "knowledge_type": stmt.excluded.knowledge_type,
                    },
                )

                db.execute(stmt)

            db.commit()

        finally:
            db.close()

    def count(self) -> int:
        db = SessionLocal()

        try:
            return db.query(KnowledgeChunkRecord).count()

        finally:
            db.close()
