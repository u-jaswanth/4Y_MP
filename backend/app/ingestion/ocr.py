import io

import pymupdf
import pytesseract

from PIL import Image

from .models import StructuredDocument


def ocr_page(page) -> str:

    # Convert PDF page to image
    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    # Convert image bytes to PIL image
    image = Image.open(
        io.BytesIO(
            pixmap.tobytes("png")
        )
    )

    # Run OCR
    text = pytesseract.image_to_string(
        image
    )

    return text


def add_ocr_fallback(
    document: StructuredDocument,
    min_text_chars: int = 40
) -> StructuredDocument:

    pdf = pymupdf.open(
        document.source_file
    )

    for page_data in document.pages:

        existing_text = (
            page_data.text.strip()
        )

        # Text extraction worked.
        # No OCR needed.
        if len(existing_text) >= min_text_chars:
            continue

        # Text extraction produced
        # little/no useful text.
        page = pdf[
            page_data.page_number - 1
        ]

        ocr_text = ocr_page(page)

        # Use OCR only when it gives
        # more text than normal extraction.
        if len(ocr_text.strip()) > len(
            existing_text
        ):

            page_data.text = ocr_text

            page_data.extraction_method = "ocr"

            page_data.text_length = len(
                ocr_text
            )

    pdf.close()

    return document