from app.ingestion.models import (
    StructuredDocument
)

from .llm import (
    DocumentUnderstandingLLM
)

from .schemas import (
    UniversalMedicalDocument
)


def prepare_text(
    document: StructuredDocument
) -> str:

    blocks = []

    for page in document.pages:

        block = (
            f"=== PAGE "
            f"{page.page_number} ===\n\n"
            f"{page.text}"
        )

        blocks.append(block)

    return "\n\n".join(blocks)


def understand_document(
    document: StructuredDocument
) -> UniversalMedicalDocument:

    document_id = (
        document
        .metadata
        .get(
            "document_id",
            "unknown-document"
        )
    )

    cleaned_text = prepare_text(
        document
    )

    llm = DocumentUnderstandingLLM()

    result = llm.understand(
        document_id=document_id,
        cleaned_text=cleaned_text
    )

    return result