from pathlib import Path

import pymupdf

from .models import (
    PageContent,
    StructuredDocument
)


def load_pdf(
    file_path: Path
) -> StructuredDocument:

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    pdf = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(
        pdf,
        start=1
    ):

        text = page.get_text("text") or ""

        page_data = PageContent(
            page_number=page_number,
            text=text,
            extraction_method="text",
            text_length=len(text)
        )

        pages.append(page_data)

    document = StructuredDocument(
        source_file=str(file_path),
        file_type="application/pdf",
        page_count=len(pages),
        pages=pages,
        metadata={
            "filename": file_path.name
        }
    )

    pdf.close()

    return document