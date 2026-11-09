
# class RAGContextBuilder:

#     def build(self, query: str, retrieval_result: dict) -> str:

#         patient = retrieval_result.get("patient", {})

#         observations = patient.get("observations", [])
#         knowledge = retrieval_result.get("knowledge", [])

#         context_parts = []

#         # ==================================================
#         # USER QUESTION
#         # ==================================================

#         context_parts.append(f"""
# USER QUESTION
# =============
# {query}
# """)

#         # ==================================================
#         # PATIENT OBSERVATIONS
#         # ==================================================

#         context_parts.append("""
# PATIENT MEDICAL RECORDS
# =======================

# The following information comes from the patient's
# uploaded medical records.

# Patient records are authoritative for
# patient-specific facts.
# """)

#         if observations:

#             for i, observation in enumerate(
#                 observations,
#                 start=1
#             ):

#                 metadata = observation.get(
#                     "metadata",
#                     {}
#                 )

#                 context_parts.append(f"""
# Patient Observation {i}

# Test name:
# {metadata.get("observation_name", "not specified")}

# Canonical name:
# {metadata.get("canonical_name", "not specified")}

# Document ID:
# {metadata.get("document_id", "not specified")}

# Source page:
# {metadata.get("source_page", "not specified")}

# Evidence:
# {observation.get("document", "")}
# """)

#         else:

#             context_parts.append(
#                 "No relevant patient observations were retrieved."
#             )

#         # ==================================================
#         # MEDICAL KNOWLEDGE
#         # ==================================================

#         context_parts.append("""
# GENERAL MEDICAL KNOWLEDGE
# =========================

# The following information comes from the medical
# knowledge base.

# Use it for general medical explanations,
# causes, mechanisms, terminology, and clinical concepts.
# """)

#         if knowledge:

#             for i, item in enumerate(
#                 knowledge,
#                 start=1
#             ):

#                 context_parts.append(f"""
# Medical Knowledge {i}

# Source:
# {item.get("source", "not specified")}

# Textbook:
# {item.get("title", "not specified")}

# Content:
# {item.get("content", "")}
# """)

#         else:

#             context_parts.append(
#                 "No relevant medical knowledge was retrieved."
#             )

#         return "\n".join(context_parts)


class RAGContextBuilder:

    def build(
        self,
        query: str,
        retrieval_result: dict
    ) -> str:

        patient = retrieval_result.get(
            "patient",
            {}
        )

        observations = patient.get(
            "observations",
            []
        )

        knowledge = retrieval_result.get(
            "knowledge",
            []
        )

        context_parts = []

        # --------------------------------------------------
        # USER QUESTION
        # --------------------------------------------------

        context_parts.append(
            f"""
USER QUESTION
=============

{query}
"""
        )

        # --------------------------------------------------
        # PATIENT RECORDS
        # --------------------------------------------------

        context_parts.append(
            """
PATIENT MEDICAL RECORDS
=======================

The following observations come from the
patient's uploaded medical records.

Patient-specific facts must come from these records.
"""
        )

        if observations:

            for i, observation in enumerate(
                observations,
                start=1
            ):

                metadata = observation.get(
                    "metadata",
                    {}
                )

                evidence = observation.get(
                    "document",
                    ""
                )

                context_parts.append(
                    f"""
Patient Observation {i}

Test:
{metadata.get("observation_name", "not specified")}

Canonical name:
{metadata.get("canonical_name", "not specified")}

Result:
{self._extract_field(evidence, "Result")}

Unit:
{self._extract_field(evidence, "Unit")}

Reference range:
{self._extract_field(evidence, "Reference range")}

Status:
{self._extract_field(evidence, "Status")}
"""
                )

        else:

            context_parts.append(
                "No relevant patient observations were retrieved."
            )

        # --------------------------------------------------
        # GENERAL MEDICAL KNOWLEDGE
        # --------------------------------------------------

        context_parts.append(
            """
GENERAL MEDICAL KNOWLEDGE
=========================

The following information comes from the
medical knowledge base.

Use it for general medical explanations,
medical concepts, causes, mechanisms,
terminology, and clinical context.
"""
        )

        if knowledge:

            for i, item in enumerate(
                knowledge,
                start=1
            ):

                context_parts.append(
                    f"""
Medical Knowledge {i}

Source:
{item.get("source", "not specified")}

Textbook:
{item.get("title", "not specified")}

Content:
{item.get("content", "")}
"""
                )

        else:

            context_parts.append(
                "No relevant medical knowledge was retrieved."
            )

        return "\n".join(context_parts)

    # --------------------------------------------------
    # Extract a field from observation evidence
    # --------------------------------------------------

    @staticmethod
    def _extract_field(
        evidence: str,
        field_name: str
    ) -> str:

        prefix = f"{field_name}:"

        for line in evidence.splitlines():

            line = line.strip()

            if line.startswith(prefix):

                value = line[
                    len(prefix):
                ].strip()

                return value or "not specified"

        return "not specified"