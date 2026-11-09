from pathlib import Path

from .pdf_loader import load_pdf
from .ocr import add_ocr_fallback


def extract_document(
    file_path: Path
):

    # Step 1:
    # Normal PDF text extraction
    document = load_pdf(
        file_path
    )

    # Step 2:
    # OCR only where necessary
    document = add_ocr_fallback(
        document
    )

    return document