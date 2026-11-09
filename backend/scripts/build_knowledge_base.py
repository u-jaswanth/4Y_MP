"""
Populates the general medical knowledge base (`vector_knowledge_chunks`,
Postgres/pgvector) from the MedRAG/textbooks dataset.

This was previously missing: `MedicalKnowledgeStore` and
`MedicalKnowledgeRetriever` existed and were wired into
`CombinedRetriever`, but nothing ever loaded data into that
collection, so every chatbot answer's "GENERAL MEDICAL KNOWLEDGE"
section was always empty in practice.

Usage (from backend/, with the venv active and .env configured):

    python scripts/build_knowledge_base.py                 # load everything (large, ~free-text books)
    python scripts/build_knowledge_base.py --limit 2000     # load a small slice for local testing

This downloads the MedRAG/textbooks dataset via `datasets` the first
time it runs, and re-embeds each chunk with the same BGE-M3 model used
everywhere else in the pipeline, so it can take a while for the full
dataset. Re-running it is safe - inserts are upserts keyed by chunk id.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.embedder import MedicalEmbedder  # noqa: E402
from app.knowledge.knowledge_store import MedicalKnowledgeStore  # noqa: E402
from app.knowledge.textbook_loader import MedicalTextbookLoader  # noqa: E402
from app.vectorstore.bootstrap import ensure_pgvector_extension  # noqa: E402

BATCH_SIZE = 64


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Dataset index to start from (default: 0)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of chunks to load (default: all)",
    )

    args = parser.parse_args()

    ensure_pgvector_extension()

    print("Loading MedRAG/textbooks dataset (this can take a while the first time)...")
    loader = MedicalTextbookLoader()
    chunks = loader.get_chunks(start=args.start, limit=args.limit)
    print(f"Loaded {len(chunks)} chunks to embed and index.")

    embedder = MedicalEmbedder()
    store = MedicalKnowledgeStore()

    start_time = time.perf_counter()

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]

        texts = [chunk["content"] for chunk in batch]
        embeddings = embedder.embed_batch(texts, batch_size=BATCH_SIZE)

        store.add_chunks(batch, embeddings)

        done = min(batch_start + BATCH_SIZE, len(chunks))
        print(f"  indexed {done}/{len(chunks)} chunks")

    elapsed = time.perf_counter() - start_time

    print(
        f"Done. Knowledge base now has {store.count()} chunks "
        f"(took {elapsed:.1f}s)."
    )


if __name__ == "__main__":
    main()
