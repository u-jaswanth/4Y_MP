# app/preprocessing/cleaner.py

import re

from app.ingestion.models import StructuredDocument


def normalize_whitespace(text: str) -> str:

    # Remove null characters
    text = text.replace("\x00", " ")

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces/tabs
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def remove_pdf_noise(text: str) -> str:

    cleaned_lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        # Obvious PDF/report presentation noise
        noise_patterns = [
            "scan to download",
            "~~~ end of report ~~~",
        ]

        if any(
            pattern in lower
            for pattern in noise_patterns
        ):
            continue

        # Page-number footer
        if re.fullmatch(
            r"page \d+ of \d+",
            lower
        ):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def clean_page_text(text: str) -> str:

    text = normalize_whitespace(text)

    text = remove_pdf_noise(text)

    return text


def clean_document(
    document: StructuredDocument
) -> StructuredDocument:

    for page in document.pages:

        page.text = clean_page_text(
            page.text
        )

        page.text_length = len(
            page.text
        )

    return document