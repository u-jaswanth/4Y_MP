from typing import Any, Optional

from pydantic import BaseModel, Field


class RAGChunk(BaseModel):

    chunk_id: str

    document_id: str

    document_type: str

    subtype: Optional[str] = None

    content: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )