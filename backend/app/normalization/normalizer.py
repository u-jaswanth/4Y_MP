# from app.understanding.schemas import (
#     UniversalMedicalDocument,
#     Observation
# )

# from .models import NormalizedObservation


# class MedicalNormalizer:

#     def normalize_observation(
#         self,
#         observation: Observation
#     ) -> NormalizedObservation:

#         canonical_name = (
#             self._normalize_name(
#                 observation.name
#             )
#         )

#         return NormalizedObservation(
#             original_name=observation.name,
#             canonical_name=canonical_name,
#             value=observation.value,
#             unit=observation.unit,
#             reference_range=(
#                 observation.reference_range
#             ),
#             status=observation.status,
#             specimen=observation.specimen,
#             notes=observation.notes,
#             source_page=observation.source_page
#         )


#     def _normalize_name(
#         self,
#         name: str
#     ) -> str:

#         normalized = name.strip().lower()

#         return normalized


#     def normalize_document(
#         self,
#         document: UniversalMedicalDocument
#     ) -> list[NormalizedObservation]:

#         normalized_observations = []

#         for section in document.sections:

#             for observation in section.observations:

#                 normalized = (
#                     self.normalize_observation(
#                         observation
#                     )
#                 )

#                 normalized_observations.append(
#                     normalized
#                 )

#         return normalized_observations






from app.understanding.schemas import (
    UniversalMedicalDocument,
    Observation
)

from .models import NormalizedObservation
from .terminology import MedicalTerminology


class MedicalNormalizer:

    def __init__(self):
        self.terminology = MedicalTerminology()

    def normalize_observation(
        self,
        observation: Observation
    ) -> NormalizedObservation:

        terminology_result = (
            self.terminology.resolve(
                observation.name
            )
        )

        if terminology_result:

            canonical_name = (
                terminology_result["canonical_name"]
            )

            aliases = (
                terminology_result["aliases"]
            )

        else:

            canonical_name = (
                self._normalize_name(
                    observation.name
                )
            )

            aliases = []

        return NormalizedObservation(
            original_name=observation.name,
            canonical_name=canonical_name,
            aliases=aliases,
            value=observation.value,
            unit=observation.unit,
            reference_range=(
                observation.reference_range
            ),
            status=observation.status,
            specimen=observation.specimen,
            notes=observation.notes,
            source_page=observation.source_page
        )

    def _normalize_name(
        self,
        name: str
    ) -> str:

        normalized = name.strip().lower()

        return normalized

    def normalize_document(
        self,
        document: UniversalMedicalDocument
    ) -> list[NormalizedObservation]:

        normalized_observations = []

        for section in document.sections:

            for observation in section.observations:

                normalized = (
                    self.normalize_observation(
                        observation
                    )
                )

                normalized_observations.append(
                    normalized
                )

        return normalized_observations