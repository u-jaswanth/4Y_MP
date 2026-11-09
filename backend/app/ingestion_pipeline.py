"""
Runs a single uploaded PDF report through the full ingestion ->
understanding -> normalization -> chunking -> indexing pipeline,
so it becomes searchable by the RAG chatbot.

This wires together the modules that were built independently:

    ingestion.extractor.extract_document        (PDF -> pages)
    preprocessing.cleaner.clean_document        (clean page text)
    understanding.document_understanding        (LLM -> structured doc)
    normalization.normalizer.MedicalNormalizer  (canonical test names)
    chunking.chunk_builder.RAGChunkBuilder       (one RAG chunk / doc)
    embeddings.embedder.MedicalEmbedder          (BGE-M3 embeddings)
    vectorstore.pgvector_store.PgVectorStore     (full-document store, Postgres/pgvector)
    retrieval.observation_index.ObservationIndex (per-observation store, Postgres/pgvector)
"""

from pathlib import Path

from app.ingestion.extractor import extract_document
from app.preprocessing.cleaner import clean_document
from app.understanding.document_understanding import understand_document
from app.normalization.normalizer import MedicalNormalizer
from app.chunking.chunk_builder import RAGChunkBuilder
from app.embeddings.embedder import MedicalEmbedder
from app.vectorstore.pgvector_store import PgVectorStore
from app.retrieval.observation_index import ObservationIndex


def ingest_report(file_path: str, document_id: str) -> dict:
    """
    Runs one PDF report through the whole pipeline and indexes it.

    Returns a small summary dict describing what was extracted,
    so the API layer can store/report it.
    """

    path = Path(file_path)

    # 1. Extract raw text (with OCR fallback for scanned pages)
    document = extract_document(path)
    document.metadata["document_id"] = document_id

    # 2. Clean page text
    document = clean_document(document)

    # 3. LLM structure extraction -> UniversalMedicalDocument
    universal_document = understand_document(document)
    universal_document.document_id = document_id

    # 4. Normalize observation names (canonical names + aliases)
    normalizer = MedicalNormalizer()
    normalized_observations = normalizer.normalize_document(universal_document)

    # 5. Build one RAG chunk representing the whole document
    chunk = RAGChunkBuilder().build(universal_document, normalized_observations)

    # 6. Embed + index (shared embedder for both stores)
    embedder = MedicalEmbedder()

    document_store = PgVectorStore()
    document_store.add_chunk(
        chunk_id=chunk.chunk_id,
        content=chunk.content,
        embedding=embedder.embed(chunk.content),
        metadata=chunk.metadata,
    )

    observation_index = ObservationIndex(embedder=embedder)
    observation_index.add_document(universal_document, normalized_observations)

    total_observations = sum(
        len(section.observations) for section in universal_document.sections
    )

    return {
        "document_id": document_id,
        "document_type": universal_document.document_type,
        "subtype": universal_document.subtype,
        "sections": len(universal_document.sections),
        "observations_indexed": total_observations,
    }
