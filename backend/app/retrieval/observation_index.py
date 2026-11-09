import re

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.embeddings.embedder import MedicalEmbedder
from app.vectorstore.models import ObservationRecord


class ObservationIndex:
    """
    Per-observation semantic + name-matching index, now backed by
    Postgres/pgvector instead of a local Chroma collection.

    Public interface (add_document / search / count) is unchanged
    from the Chroma version, so RAGRetriever doesn't need to change.
    """

    def __init__(self, embedder=None):
        # Use shared embedder if provided.
        # Otherwise create one for backward compatibility.
        self.embedder = embedder or MedicalEmbedder()

    def add_document(self, structured_document, normalized_observations):

        document_id = structured_document.document_id

        rows = []
        normalized_index = 0

        for section in structured_document.sections:

            for observation in section.observations:

                normalized = normalized_observations[normalized_index]
                normalized_index += 1

                observation_id = (
                    f"{document_id}_"
                    f"{observation.source_page}_"
                    f"{observation.name}"
                )

                aliases = normalized.aliases
                alias_text = ", ".join(aliases) if aliases else "none"

                text = (
                    f"Medical observation\n"
                    f"Test name: {observation.name}\n"
                    f"Canonical name: {normalized.canonical_name}\n"
                    f"Aliases: {alias_text}\n"
                    f"Result: {observation.value}\n"
                    f"Unit: {observation.unit or 'not specified'}\n"
                    f"Reference range: "
                    f"{observation.reference_range or 'not specified'}\n"
                    f"Status: {observation.status or 'not specified'}"
                )

                vector = self.embedder.embed(text)

                rows.append(
                    {
                        "id": observation_id,
                        "document_id": document_id,
                        "content": text,
                        "embedding": vector,
                        "observation_name": observation.name,
                        "canonical_name": normalized.canonical_name,
                        "aliases": alias_text,
                        "source_page": observation.source_page,
                        "section_type": section.section_type,
                    }
                )

        if not rows:
            return

        db = SessionLocal()

        try:
            for row in rows:
                stmt = pg_insert(ObservationRecord).values(**row)

                stmt = stmt.on_conflict_do_update(
                    index_elements=[ObservationRecord.id],
                    set_={
                        "document_id": stmt.excluded.document_id,
                        "content": stmt.excluded.content,
                        "embedding": stmt.excluded.embedding,
                        "observation_name": stmt.excluded.observation_name,
                        "canonical_name": stmt.excluded.canonical_name,
                        "aliases": stmt.excluded.aliases,
                        "source_page": stmt.excluded.source_page,
                        "section_type": stmt.excluded.section_type,
                    },
                )

                db.execute(stmt)

            db.commit()

        finally:
            db.close()

    def _normalize_text(self, text: str) -> str:

        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _name_match_score(
        self,
        query: str,
        observation_name: str,
        canonical_name: str,
        aliases: str,
    ) -> float:

        query = self._normalize_text(query)

        candidates = [observation_name, canonical_name]

        if aliases and aliases != "none":
            candidates.extend(aliases.split(", "))

        best_score = 0.0

        for candidate in candidates:

            candidate = self._normalize_text(candidate)

            if not candidate:
                continue

            if query == candidate:
                score = 1.0
            elif query in candidate:
                score = 0.9
            elif candidate in query:
                score = 0.85
            else:
                query_words = set(query.split())
                candidate_words = set(candidate.split())
                overlap = query_words.intersection(candidate_words)

                if overlap:
                    score = len(overlap) / max(
                        len(query_words), len(candidate_words)
                    )
                else:
                    score = 0.0

            best_score = max(best_score, score)

        return best_score

    @staticmethod
    def _empty_result() -> dict:
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "hybrid_scores": [[]],
            "name_scores": [[]],
            "semantic_scores": [[]],
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ):
        """
        document_ids, when provided, restricts the search to
        observations belonging to that set of document_ids (used to
        scope retrieval to a single patient's own reports so
        patients never see each other's data).
        """

        query = query.strip()

        if not query:
            return self._empty_result()

        if document_ids is not None and len(document_ids) == 0:
            # Patient has no analyzed reports yet - nothing to search.
            return self._empty_result()

        db = SessionLocal()

        try:
            base_query = db.query(ObservationRecord)

            if document_ids is not None:
                base_query = base_query.filter(
                    ObservationRecord.document_id.in_(document_ids)
                )

            total_count = base_query.count()

            if total_count == 0:
                return self._empty_result()

            candidate_k = min(max(top_k * 3, 10), total_count)

            query_vector = self.embedder.embed(query)

            distance_column = ObservationRecord.embedding.cosine_distance(
                query_vector
            ).label("distance")

            ranked_query = db.query(ObservationRecord, distance_column)

            if document_ids is not None:
                ranked_query = ranked_query.filter(
                    ObservationRecord.document_id.in_(document_ids)
                )

            rows = (
                ranked_query.order_by(distance_column)
                .limit(candidate_k)
                .all()
            )

        finally:
            db.close()

        ranked_results = []

        for record, distance in rows:

            name_score = self._name_match_score(
                query,
                record.observation_name or "",
                record.canonical_name or "",
                record.aliases or "none",
            )

            distance = float(distance)
            semantic_score = 1 / (1 + distance)

            hybrid_score = 0.65 * name_score + 0.35 * semantic_score

            metadata = {
                "document_id": record.document_id,
                "observation_name": record.observation_name,
                "canonical_name": record.canonical_name,
                "aliases": record.aliases,
                "source_page": record.source_page,
                "section_type": record.section_type,
            }

            ranked_results.append(
                {
                    "document": record.content,
                    "metadata": metadata,
                    "distance": distance,
                    "name_score": name_score,
                    "semantic_score": semantic_score,
                    "hybrid_score": hybrid_score,
                }
            )

        ranked_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        ranked_results = ranked_results[:top_k]

        return {
            "documents": [[item["document"] for item in ranked_results]],
            "metadatas": [[item["metadata"] for item in ranked_results]],
            "distances": [[item["distance"] for item in ranked_results]],
            "hybrid_scores": [
                [item["hybrid_score"] for item in ranked_results]
            ],
            "name_scores": [[item["name_score"] for item in ranked_results]],
            "semantic_scores": [
                [item["semantic_score"] for item in ranked_results]
            ],
        }

    def count(self) -> int:
        db = SessionLocal()

        try:
            return db.query(ObservationRecord).count()

        finally:
            db.close()
