"""
Validation layer for smart-doc-extractor.

Takes the structured fields produced by field_extractor.py and decides
whether the extraction is trustworthy enough to use automatically, or
whether it needs a human to look at it. This is the layer that turns
"we ran some regex" into "we have a quality gate" — the difference
between a script and a pipeline.

Rules are intentionally simple and explicit (not ML-based) for Week 1.
Each rule is independently testable and explainable, which matters
more at this stage than marginal accuracy gains from a fancier model.
"""

from dataclasses import dataclass

from field_extractor import ResumeFields

# Required fields — missing any of these drops the result to "needs_review".
REQUIRED_FIELDS = ["name", "email"]

# A skills list shorter than this is suspicious for a technical resume,
# but not necessarily wrong — it's a soft warning, not a hard failure.
MIN_EXPECTED_SKILLS = 2


@dataclass
class ValidationResult:
    status: str  # "passed", "needs_review", "failed"
    issues: list[str]

    def to_dict(self) -> dict:
        return {"status": self.status, "issues": self.issues}


def validate(fields: ResumeFields, extraction_method: str, chars_per_page: float) -> ValidationResult:
    issues: list[str] = []

    # Hard failure: extraction produced almost nothing at all, regardless
    # of method. This usually means the file was corrupt, password
    # protected, or a non-resume document entirely.
    if chars_per_page < 10:
        issues.append("extraction_yielded_almost_no_text")
        return ValidationResult(status="failed", issues=issues)

    # Required field checks.
    for required in REQUIRED_FIELDS:
        if not getattr(fields, required):
            issues.append(f"missing_required_field:{required}")

    # Soft checks — don't fail the result, but flag for review.
    if not fields.phone:
        issues.append("missing_phone")
    if len(fields.skills) < MIN_EXPECTED_SKILLS:
        issues.append("skills_list_too_short")
    if extraction_method == "tesseract_ocr":
        # OCR is inherently less reliable than direct text extraction —
        # flag every OCR-derived result for review, even if every field
        # looks fine, since OCR can silently corrupt characters (e.g.
        # "CI/CD" becoming "Cl/CD") without raising an error.
        issues.append("ocr_derived_recommend_spot_check")

    if any(issue.startswith("missing_required_field") for issue in issues):
        status = "needs_review"
    elif issues:
        status = "needs_review"
    else:
        status = "passed"

    return ValidationResult(status=status, issues=issues)
