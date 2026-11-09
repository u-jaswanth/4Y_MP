from app.database import SessionLocal
from app.embeddings.embedder import MedicalEmbedder
from app.vectorstore.models import KnowledgeChunkRecord


class MedicalKnowledgeRetriever:
    """
    Retrieves relevant medical knowledge from the medical textbook
    knowledge base (Postgres/pgvector-backed).
    """

    def __init__(self, top_k=5, embedder=None):

        self.top_k = top_k

        # Use shared embedder if provided.
        # Otherwise create one for backward compatibility.
        self.embedder = embedder or MedicalEmbedder()

    def retrieve(self, query: str):
        """
        Retrieve the most relevant medical knowledge chunks.
        """

        query = query.strip()

        if not query:
            return []

        db = SessionLocal()

        try:
            count = db.query(KnowledgeChunkRecord).count()

            if count == 0:
                # Knowledge base hasn't been populated yet
                # (see backend/scripts/build_knowledge_base.py).
                return []

            query_embedding = self.embedder.embed(query)

            distance_column = KnowledgeChunkRecord.embedding.cosine_distance(
                query_embedding
            ).label("distance")

            rows = (
                db.query(KnowledgeChunkRecord, distance_column)
                .order_by(distance_column)
                .limit(min(self.top_k, count))
                .all()
            )

        finally:
            db.close()

        retrieved = []

        for record, distance in rows:

            retrieved.append(
                {
                    "content": record.content,
                    "title": record.title,
                    "source": record.source,
                    "knowledge_type": record.knowledge_type,
                    "distance": float(distance),
                }
            )

        return retrieved
