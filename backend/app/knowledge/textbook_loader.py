from datasets import load_dataset


class MedicalTextbookLoader:
    """
    Loads the pre-chunked MedRAG medical textbook dataset.

    Each dataset record becomes one knowledge chunk.
    """

    def __init__(self, dataset_name="MedRAG/textbooks"):
        self.dataset_name = dataset_name
        self.dataset = None

    def load(self):
        """Load the complete dataset."""

        self.dataset = load_dataset(
            self.dataset_name,
            split="train"
        )

        return self.dataset

    def get_chunks(self, start=0, limit=None):
        """
        Return normalized knowledge chunks.

        Args:
            start: Starting dataset index.
            limit: Maximum number of chunks to return.
                   None means from start to the end.
        """

        if self.dataset is None:
            self.load()

        total = len(self.dataset)

        if start >= total:
            return []

        if limit is None:
            end = total
        else:
            end = min(start + limit, total)

        chunks = []

        for i in range(start, end):

            record = self.dataset[i]

            content = record.get("content", "")

            # Skip empty chunks
            if not content or not content.strip():
                continue

            chunk = {
                "chunk_id": record["id"],
                "title": record["title"],
                "content": content.strip(),
                "source": "MedRAG Textbooks",
                "knowledge_type": "medical_textbook"
            }

            chunks.append(chunk)

        return chunks

    def count(self):
        """Return total number of records."""

        if self.dataset is None:
            self.load()

        return len(self.dataset)