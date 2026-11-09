from typing import Any

from pydantic import BaseModel, Field


class PageContent(BaseModel):
    page_number: int

    text: str = ""

    extraction_method: str = "text"

    text_length: int = 0

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class StructuredDocument(BaseModel):
    source_file: str

    file_type: str

    page_count: int

    pages: list[PageContent]

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )