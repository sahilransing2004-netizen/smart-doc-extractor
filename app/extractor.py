"""
Core extraction logic for smart-doc-extractor.

Strategy (hybrid approach):
1. Try direct text extraction from the PDF (works for born-digital resumes
   made in Word, Canva, LaTeX, etc.) using pdfplumber.
2. If that yields little or no usable text (i.e. the PDF is a scanned
   image with no text layer), fall back to Tesseract OCR on rasterized
   page images.

This avoids the common mistake of running every PDF through OCR, which
degrades quality on PDFs that already have clean, extractable text.
"""

import io
import logging

import pdfplumber
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# If direct extraction yields fewer than this many characters per page
# on average, we treat the PDF as "no usable text layer" and fall back
# to OCR. Real resumes have way more text than this per page; a low
# count almost always means the page is a scanned image.
MIN_CHARS_PER_PAGE_THRESHOLD = 30


class ExtractionResult:
    """Holds the outcome of an extraction attempt, plus metadata about
    which method was used. The 'method' field is important: it's exactly
    the kind of decision an interviewer will ask you to justify."""

    def __init__(self, text: str, method: str, pages: int, chars_per_page: float):
        self.text = text
        self.method = method  # "direct_text" or "tesseract_ocr"
        self.pages = pages
        self.chars_per_page = chars_per_page

    def __repr__(self):
        return (
            f"ExtractionResult(method={self.method!r}, pages={self.pages}, "
            f"chars_per_page={self.chars_per_page:.1f}, "
            f"text_len={len(self.text)})"
        )


def _extract_direct_text(pdf_path: str) -> tuple[str, int]:
    """Attempt direct text extraction using pdfplumber.
    Returns (combined_text, page_count)."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts), page_count


def _extract_via_ocr(pdf_path: str) -> str:
    """Fallback path: rasterize each page to an image and run Tesseract
    OCR on it. Used when the PDF has no usable text layer (i.e. it's a
    scanned image)."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Render page to a PIL image at a reasonable DPI for OCR accuracy.
            pil_image = page.to_image(resolution=300).original
            ocr_text = pytesseract.image_to_string(pil_image)
            text_parts.append(ocr_text)
    return "\n".join(text_parts)


def extract_text(pdf_path: str) -> ExtractionResult:
    """Main entry point. Tries direct text extraction first; falls back
    to OCR only if the direct extraction looks like it failed (i.e. the
    PDF is image-based, not text-based)."""

    direct_text, page_count = _extract_direct_text(pdf_path)
    chars_per_page = len(direct_text.strip()) / max(page_count, 1)

    if chars_per_page >= MIN_CHARS_PER_PAGE_THRESHOLD:
        logger.info(
            "Direct text extraction succeeded (%.1f chars/page) — skipping OCR",
            chars_per_page,
        )
        return ExtractionResult(
            text=direct_text,
            method="direct_text",
            pages=page_count,
            chars_per_page=chars_per_page,
        )

    logger.info(
        "Direct text extraction looks empty (%.1f chars/page) — falling back to OCR",
        chars_per_page,
    )
    ocr_text = _extract_via_ocr(pdf_path)
    return ExtractionResult(
        text=ocr_text,
        method="tesseract_ocr",
        pages=page_count,
        chars_per_page=len(ocr_text.strip()) / max(page_count, 1),
    )
