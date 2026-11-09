from sentence_transformers import SentenceTransformer


class MedicalEmbedder:

    def __init__(self):
        self.model = SentenceTransformer(
            "BAAI/bge-m3",
            device="cpu"
        )

    def embed(
        self,
        text: str
    ) -> list[float]:

        embedding = self.model.encode(
            text,
            normalize_embeddings=True
        )

        return embedding.tolist()

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32
    ) -> list[list[float]]:

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        return embeddings.tolist()


# Load the embedding model ONCE per FastAPI process.
medical_embedder = MedicalEmbedder()