from typing import Any, Optional

from pydantic import BaseModel, Field


class Identifier(BaseModel):
    type: str
    value: str


class PatientInfo(BaseModel):
    name: Optional[str] = None

    age: Optional[str] = None

    sex: Optional[str] = None

    identifiers: list[Identifier] = Field(
        default_factory=list
    )


class EncounterInfo(BaseModel):
    date: Optional[str] = None

    doctor: Optional[str] = None

    organization: Optional[str] = None

    department: Optional[str] = None


class Observation(BaseModel):
    name: str

    value: Optional[str] = None

    unit: Optional[str] = None

    reference_range: Optional[str] = None

    status: Optional[str] = None

    specimen: Optional[str] = None

    notes: Optional[str] = None

    source_page: Optional[int] = None


class SemanticSection(BaseModel):
    section_type: str

    title: str

    content: Optional[str] = None

    observations: list[Observation] = Field(
        default_factory=list
    )

    source_pages: list[int] = Field(
        default_factory=list
    )


class UniversalMedicalDocument(BaseModel):
    document_id: str

    document_type: str

    subtype: Optional[str] = None

    patient: PatientInfo = Field(
        default_factory=PatientInfo
    )

    encounter: EncounterInfo = Field(
        default_factory=EncounterInfo
    )

    sections: list[SemanticSection] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    source_pages: list[int] = Field(
        default_factory=list
    )