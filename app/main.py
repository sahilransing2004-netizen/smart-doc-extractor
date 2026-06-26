"""
FastAPI application for smart-doc-extractor.

Exposes a single endpoint: upload a resume PDF, get back structured
JSON. This wraps extractor.py (text extraction with OCR fallback) and
field_extractor.py (structured field parsing) behind an HTTP interface.

Run locally with:
    uvicorn app.main:app --reload
"""

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .extractor import extract_text
from .field_extractor import extract_fields
from .validator import validate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="smart-doc-extractor",
    description="Extracts structured fields from resume PDFs using a hybrid "
    "direct-text/OCR-fallback pipeline.",
    version="0.1.0",
)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB — resumes are small; reject anything absurd


@app.get("/health")
def health_check():
    """Basic liveness check — used by monitoring/orchestration later on."""
    return {"status": "ok"}


@app.post("/extract")
async def extract_resume(file: UploadFile = File(...)):
    """Accepts a single PDF resume, runs it through the extraction
    pipeline, and returns structured fields as JSON."""

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Expected a PDF file, got content-type '{file.content_type}'",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Write to a temp file because pdfplumber/pytesseract need a real
    # file path, not an in-memory buffer.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        extraction = extract_text(tmp_path)
        fields = extract_fields(extraction.text)
        validation = validate(fields, extraction.method, extraction.chars_per_page)
    except Exception as exc:
        logger.exception("Extraction failed for uploaded file %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    response_body = fields.to_dict()
    response_body["validation"] = validation.to_dict()
    response_body["_meta"] = {
        "filename": file.filename,
        "extraction_method": extraction.method,
        "pages": extraction.pages,
    }
    return JSONResponse(content=response_body)
