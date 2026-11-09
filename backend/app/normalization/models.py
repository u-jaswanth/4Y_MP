from typing import Optional

from pydantic import BaseModel, Field


class NormalizedObservation(BaseModel):

    original_name: str

    canonical_name: Optional[str] = None

    aliases: list[str] = Field(default_factory=list)

    value: Optional[str] = None

    unit: Optional[str] = None

    reference_range: Optional[str] = None

    status: Optional[str] = None

    specimen: Optional[str] = None

    notes: Optional[str] = None

    source_page: Optional[int] = None