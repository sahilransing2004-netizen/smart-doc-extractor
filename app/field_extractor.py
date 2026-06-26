"""
Structured field extraction from raw resume text.

This takes whatever text came out of extractor.py (regardless of whether
it came from direct text extraction or OCR) and pulls out structured
fields: name, email, phone, skills, and section blocks (summary,
experience, education).

Design note: resumes have no fixed schema, so this uses a mix of regex
for high-confidence fields (email, phone — these have a strict format)
and section-header detection for looser fields (skills, experience,
education — these vary a lot between resumes). This is a deliberate
middle ground between "pure regex" (fails on loosely structured
sections) and "send everything to an LLM" (overkill and costly for
fields that are trivially regex-matchable).
"""

import re
from dataclasses import dataclass, field


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")

# Common section headers found on resumes. Matched case-insensitively,
# at the start of a line, since that's how most resumes format them.
SECTION_HEADERS = [
    "summary",
    "skills",
    "experience",
    "work experience",
    "education",
    "projects",
    "certifications",
]


@dataclass
class ResumeFields:
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)

    # Flags raised during extraction — useful for the validation layer
    # downstream, and for an interviewer asking "how do you know when
    # extraction quality is low".
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "sections": self.sections,
            "warnings": self.warnings,
        }


def _extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    match = PHONE_PATTERN.search(text)
    if not match:
        return None
    candidate = match.group(0)
    # Guard against false positives: a bare run of digits that's too
    # short to be a real phone number (e.g. a year, a zip code).
    digit_count = sum(c.isdigit() for c in candidate)
    if digit_count < 7:
        return None
    return candidate.strip()


def _extract_name(lines: list[str]) -> str | None:
    """Heuristic: the name is almost always the first non-empty line,
    as long as it doesn't look like an email/phone/section header and
    isn't suspiciously long (which would suggest it's actually a
    summary sentence, not a name)."""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if EMAIL_PATTERN.search(stripped) or PHONE_PATTERN.search(stripped):
            continue
        if stripped.lower() in SECTION_HEADERS:
            continue
        word_count = len(stripped.split())
        if 1 <= word_count <= 5 and len(stripped) <= 50:
            return stripped
        return None  # first real line didn't look like a name — bail
    return None


def _split_into_sections(lines: list[str]) -> dict[str, str]:
    """Walk the lines and group them under whichever section header
    they fall under. Lines before the first recognized header are
    ignored here (name/email/phone already handled separately)."""
    sections: dict[str, list[str]] = {}
    current_section = None

    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered in SECTION_HEADERS:
            current_section = lowered
            sections[current_section] = []
            continue
        if current_section and stripped:
            sections[current_section].append(stripped)

    return {section: "\n".join(content) for section, content in sections.items()}


def _extract_skills(sections: dict[str, str]) -> list[str]:
    """Skills sections are usually a comma-separated list. Split on
    commas, strip whitespace, drop empties."""
    skills_text = sections.get("skills", "")
    if not skills_text:
        return []
    raw_items = skills_text.split(",")
    return [item.strip() for item in raw_items if item.strip()]


def extract_fields(text: str) -> ResumeFields:
    lines = text.split("\n")
    result = ResumeFields()

    result.name = _extract_name(lines)
    if not result.name:
        result.warnings.append("name_not_detected")

    result.email = _extract_email(text)
    if not result.email:
        result.warnings.append("email_not_detected")

    result.phone = _extract_phone(text)
    if not result.phone:
        result.warnings.append("phone_not_detected")

    result.sections = _split_into_sections(lines)
    result.skills = _extract_skills(result.sections)
    if not result.skills:
        result.warnings.append("skills_not_detected")

    return result
