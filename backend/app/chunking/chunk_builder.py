from app.understanding.schemas import (
    UniversalMedicalDocument
)

from app.normalization.models import (
    NormalizedObservation
)

from .models import RAGChunk


class RAGChunkBuilder:

    def build(
        self,
        document: UniversalMedicalDocument,
        normalized_observations: list[
            NormalizedObservation
        ]
    ) -> RAGChunk:

        content_parts = []

        # ==============================
        # DOCUMENT INFORMATION
        # ==============================

        content_parts.append(
            f"Document Type: {document.document_type}"
        )

        if document.subtype:
            content_parts.append(
                f"Document Subtype: {document.subtype}"
            )


        # ==============================
        # PATIENT INFORMATION
        # ==============================

        patient = document.patient

        patient_parts = []

        if patient.name:
            patient_parts.append(
                f"Name: {patient.name}"
            )

        if patient.age:
            patient_parts.append(
                f"Age: {patient.age}"
            )

        if patient.sex:
            patient_parts.append(
                f"Sex: {patient.sex}"
            )

        if patient.identifiers:

            for identifier in patient.identifiers:

                patient_parts.append(
                    f"{identifier.type}: "
                    f"{identifier.value}"
                )

        if patient_parts:

            content_parts.append(
                "Patient:\n"
                + "\n".join(patient_parts)
            )


        # ==============================
        # ENCOUNTER INFORMATION
        # ==============================

        encounter = document.encounter

        encounter_parts = []

        if encounter.date:
            encounter_parts.append(
                f"Date: {encounter.date}"
            )

        if encounter.doctor:
            encounter_parts.append(
                f"Doctor: {encounter.doctor}"
            )

        if encounter.organization:
            encounter_parts.append(
                f"Organization: "
                f"{encounter.organization}"
            )

        if encounter.department:
            encounter_parts.append(
                f"Department: "
                f"{encounter.department}"
            )

        if encounter_parts:

            content_parts.append(
                "Encounter:\n"
                + "\n".join(encounter_parts)
            )


        # ==============================
        # MEDICAL SECTIONS
        # ==============================

        normalized_index = 0

        for section in document.sections:

            section_parts = []

            section_parts.append(
                f"Section: {section.title}"
            )

            if section.content:

                section_parts.append(
                    f"Content:\n{section.content}"
                )


            # --------------------------
            # Observations
            # --------------------------

            for observation in section.observations:

                normalized = None

                if normalized_index < len(
                    normalized_observations
                ):
                    normalized = (
                        normalized_observations[
                            normalized_index
                        ]
                    )

                normalized_index += 1

                observation_parts = []

                if normalized:
                    observation_parts.append(
                        f"Medical Concept: "
                        f"{normalized.canonical_name}"
                    )

                observation_parts.append(
                    f"Name: {observation.name}"
                )

                if observation.value is not None:
                    observation_parts.append(
                        f"Value: {observation.value}"
                    )

                if observation.unit:
                    observation_parts.append(
                        f"Unit: {observation.unit}"
                    )

                if observation.reference_range:
                    observation_parts.append(
                        "Reference Range: "
                        f"{observation.reference_range}"
                    )

                if observation.status:
                    observation_parts.append(
                        f"Status: {observation.status}"
                    )

                if observation.specimen:
                    observation_parts.append(
                        f"Specimen: {observation.specimen}"
                    )

                if observation.notes:
                    observation_parts.append(
                        f"Notes: {observation.notes}"
                    )

                section_parts.append(
                    "\n".join(observation_parts)
                )


            content_parts.append(
                "\n".join(section_parts)
            )


        # ==============================
        # METADATA
        # ==============================

        metadata = {
            "document_id": document.document_id,
            "document_type": document.document_type,
            "subtype": document.subtype,
            "source_pages": document.source_pages,
        }


        # ==============================
        # CREATE ONE CHUNK
        # ==============================

        content = "\n\n".join(
            content_parts
        )

        return RAGChunk(

            chunk_id=(
                f"{document.document_id}_chunk_001"
            ),

            document_id=document.document_id,

            document_type=document.document_type,

            subtype=document.subtype,

            content=content,

            metadata=metadata
        )