"""PDF text extraction utilities."""
from __future__ import annotations

import io

import PyPDF2


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Return all text from a PDF file given its raw bytes."""
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
    return "\n\n".join(pages)
