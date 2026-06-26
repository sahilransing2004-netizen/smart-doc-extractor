"""
Tests for smart-doc-extractor's core pipeline: extraction, field
parsing, and validation. Run with: pytest tests/test_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.extractor import extract_text
from app.field_extractor import extract_fields
from app.validator import validate

SAMPLES = Path(__file__).parent.parent / "sample_resumes"


def test_direct_text_extraction_on_digital_pdf():
    """A born-digital PDF should be handled by direct text extraction,
    not OCR."""
    result = extract_text(str(SAMPLES / "digital_resume.pdf"))
    assert result.method == "direct_text"
    assert "Sahil Ransing" in result.text


def test_ocr_fallback_on_scanned_pdf():
    """A PDF with no text layer (image-only) should automatically fall
    back to Tesseract OCR."""
    result = extract_text(str(SAMPLES / "scanned_resume.pdf"))
    assert result.method == "tesseract_ocr"
    assert len(result.text.strip()) > 0


def test_field_extraction_pulls_email_and_skills():
    result = extract_text(str(SAMPLES / "digital_resume.pdf"))
    fields = extract_fields(result.text)
    assert fields.email == "sahil.ransing@example.com"
    assert "Python" in fields.skills
    assert "Docker" in fields.skills


def test_validation_passes_clean_digital_resume():
    result = extract_text(str(SAMPLES / "digital_resume.pdf"))
    fields = extract_fields(result.text)
    verdict = validate(fields, result.method, result.chars_per_page)
    assert verdict.status == "passed"
    assert verdict.issues == []


def test_validation_flags_ocr_derived_results_for_review():
    """Even when every field extracts cleanly, OCR-derived results
    should be flagged for review since OCR can silently corrupt
    characters without raising an error."""
    result = extract_text(str(SAMPLES / "scanned_resume.pdf"))
    fields = extract_fields(result.text)
    verdict = validate(fields, result.method, result.chars_per_page)
    assert verdict.status == "needs_review"
    assert "ocr_derived_recommend_spot_check" in verdict.issues


def test_validation_fails_on_near_empty_extraction():
    """A document that yields almost no text at all (corrupt file,
    non-resume document) should hard-fail validation."""
    result = extract_text(str(SAMPLES / "blank.pdf"))
    fields = extract_fields(result.text)
    verdict = validate(fields, result.method, result.chars_per_page)
    assert verdict.status == "failed"
    assert "extraction_yielded_almost_no_text" in verdict.issues
