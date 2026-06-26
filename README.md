# smart-doc-extractor

A document intelligence pipeline that extracts structured data from resumes — built to demonstrate end-to-end ML/DevOps engineering, not just a model in a notebook.

## Problem

Most "resume parser" projects assume every PDF needs OCR. In reality, most resumes are born-digital (made in Word, Canva, LaTeX) and already contain a clean, extractable text layer. Running OCR on these degrades accuracy for no reason. A smaller number of resumes are scanned images with no text layer at all, and those genuinely need OCR.

## Approach (Week 1)

This pipeline uses a hybrid strategy instead of defaulting to OCR for everything:

1. **Try direct text extraction first** (`pdfplumber`) — works for the majority of resumes.
2. **Check extraction quality** — if the average characters-per-page is below a threshold, the PDF is almost certainly a scanned image with no real text layer.
3. **Fall back to Tesseract OCR** only when direct extraction fails — rasterizing each page and running OCR on it.

This was a deliberate design decision, not a default — see `app/extractor.py` for the threshold logic and reasoning.

## Status

- [x] Hybrid text extraction (direct + OCR fallback) — tested against both digital and scanned sample PDFs
- [x] Structured field extraction (name, email, phone, skills, sections)
- [x] FastAPI upload endpoint (`POST /extract`, `GET /health`)
- [x] Validation layer (passed / needs_review / failed verdicts)
- [x] Automated test suite (6 tests, all passing)
- [ ] Containerization
- [ ] Deployment + live demo link
- [ ] Orchestration (Airflow/Prefect)
- [ ] Monitoring dashboard

## Running it

```bash
pip install -r requirements.txt
cd app
uvicorn main:app --reload
```

Then upload a resume PDF:
```bash
curl -X POST http://127.0.0.1:8000/extract -F "file=@resume.pdf;type=application/pdf"
```

Run tests:
```bash
pytest tests/test_pipeline.py -v
```

## API response shape

```json
{
  "name": "...",
  "email": "...",
  "phone": "...",
  "skills": ["..."],
  "sections": {"summary": "...", "experience": "...", "education": "..."},
  "warnings": [],
  "validation": {"status": "passed", "issues": []},
  "_meta": {"filename": "...", "extraction_method": "direct_text", "pages": 1}
}
```

## Project structure

```
app/             core extraction and processing logic
sample_resumes/  test PDFs (gitignored — generated locally via tests/)
tests/           test scripts and sample data generators
```

## Why this project

Built as a portfolio-grade project to demonstrate depth across the ML/DevOps stack — extraction, validation, orchestration, observability, and deployment — rather than a single static model notebook.
