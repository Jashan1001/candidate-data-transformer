"""
Resume extractor — handles both PDF and DOCX.

Strategy:
1. Extract raw text from file
2. Apply regex heuristics to find structured fields
3. Section detection for experience, education, skills blocks

This is an NLP-lite approach — production systems would use an LLM or
a dedicated resume parser here. We make this assumption explicit.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Optional

from transformer.extractors import BaseExtractor
from transformer.models.core import RawCandidate, SourceType


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
_LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w\-]+", re.I)
_GITHUB_RE = re.compile(r"github\.com/[\w\-]+", re.I)
_YOE_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience", re.I)
_YEARS_ONLY_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\b", re.I)

# Section header patterns
_SECTION_HEADERS = {
    "experience": re.compile(
        r"^(work\s+)?experience|employment\s*history|work\s*history|professional\s*experience",
        re.I | re.M,
    ),
    "education": re.compile(r"^education|academic|qualifications?", re.I | re.M),
    "skills": re.compile(
        r"^skills?|technical\s+skills?|core\s+competencies|technologies", re.I | re.M
    ),
    "summary": re.compile(
        r"^(professional\s+)?summary|objective|about\s+me|profile", re.I | re.M
    ),
}

# Date range: "Jun 2020 – Present" / "2019 - 2022" / "01/2018 - 05/2020"
_DATE_RANGE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}/\d{4}|\d{4})"
    r"\s*[-–—to]+\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}/\d{4}|\d{4}|[Pp]resent|[Cc]urrent)",
    re.I,
)


class ResumeExtractor(BaseExtractor):
    def extract(self, source_input: str | Path) -> RawCandidate:
        if isinstance(source_input, str) and not source_input.strip():
            return self._empty()

        path = Path(source_input)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            if not path.exists():
                return self._empty()
            text = self._extract_pdf(path)
            source = SourceType.RESUME_PDF
        elif suffix in {".docx", ".doc"}:
            if not path.exists():
                return self._empty()
            text = self._extract_docx(path)
            source = SourceType.RESUME_DOCX
        else:
            # Treat as raw text
            text = (
                path.read_text(encoding="utf-8", errors="ignore")
                if path.exists()
                else str(source_input)
            )
            source = SourceType.RESUME_PDF

        return self._parse_text(text, source)

    def extract_from_text(
        self, text: str, source: SourceType = SourceType.RESUME_PDF
    ) -> RawCandidate:
        """Allow injecting raw text directly (for testing)."""
        return self._parse_text(text, source)

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------

    def _extract_pdf(self, path: Path) -> str:
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                return "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                ).strip()
        except ImportError:
            raise RuntimeError("pdfplumber not installed. Run: pip install pdfplumber")
        except Exception as exc:
            raise RuntimeError(f"PDF extraction failed: {exc}")

    def _extract_docx(self, path: Path) -> str:
        try:
            from docx import Document

            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            raise RuntimeError(
                "python-docx not installed. Run: pip install python-docx"
            )
        except Exception as exc:
            raise RuntimeError(f"DOCX extraction failed: {exc}")

    # ------------------------------------------------------------------
    # Text parsing
    # ------------------------------------------------------------------

    def _parse_text(self, text: str, source: SourceType) -> RawCandidate:
        rc = RawCandidate(source=source)
        if not text or not text.strip():
            return rc

        text = text.strip()

        lines = text.splitlines()
        rc.full_name = self._extract_name(lines)
        rc.emails = _EMAIL_RE.findall(text)
        rc.phones = self._extract_phones(text)

        for m in _LINKEDIN_RE.finditer(text):
            rc.linkedin_url = (
                "https://" + m.group()
                if not m.group().startswith("http")
                else m.group()
            )
        for m in _GITHUB_RE.finditer(text):
            rc.github_url = (
                "https://" + m.group()
                if not m.group().startswith("http")
                else m.group()
            )

        sections = self._split_sections(text)
        rc.headline = self._extract_headline(sections.get("summary", ""), lines)
        rc.location_raw = self._extract_location(
            lines[:10]
        )  # location usually near top
        rc.skills_raw = self._extract_skills(sections.get("skills", ""))
        rc.experience_raw = self._extract_experience(sections.get("experience", ""))
        rc.education_raw = self._extract_education(sections.get("education", ""))

        yoe_match = _YOE_RE.search(text)
        if yoe_match:
            rc.years_experience = float(yoe_match.group(1))
        else:
            years_only_match = _YEARS_ONLY_RE.search(text)
            if years_only_match:
                rc.years_experience = float(years_only_match.group(1))

        return rc

    def _extract_name(self, lines: list[str]) -> Optional[str]:
        """First non-empty line is usually the name on a well-formatted resume."""
        for line in lines[:5]:
            stripped = line.strip()
            if (
                stripped
                and len(stripped.split()) >= 2
                and len(stripped) < 60
                and not _EMAIL_RE.search(stripped)
                and "linkedin" not in stripped.lower()
            ):
                # Must look like a name: mostly letters
                if re.match(r"^[A-Za-z\s\-\.,']+$", stripped):
                    return stripped
        return None

    def _extract_phones(self, text: str) -> list[str]:
        raw_matches = _PHONE_RE.findall(text)
        # Filter out things that look like years (4-digit numbers)
        phones = []
        for match in raw_matches:
            stripped = match.strip()
            if _DATE_RANGE_RE.fullmatch(stripped):
                continue
            if len(re.sub(r"\D", "", stripped)) >= 7:
                phones.append(stripped)
        return phones

    def _extract_location(self, lines: list[str]) -> Optional[str]:
        """Check first 10 lines for location-like patterns."""
        location_re = re.compile(
            r"[A-Za-z.\s]+,\s*[A-Z]{2}(?:,\s*[A-Za-z.\s]+)?|"
            r"[A-Za-z.\s]+,\s*[A-Za-z.\s]+,\s*[A-Za-z.\s]+",
            re.I,
        )
        for line in lines:
            m = location_re.search(line)
            if m:
                return m.group().strip()
        return None

    def _split_sections(self, text: str) -> dict[str, str]:
        """Detect section boundaries and return section text."""
        # Find all section header positions
        header_positions: list[tuple[int, str]] = []
        for section_name, pattern in _SECTION_HEADERS.items():
            for m in pattern.finditer(text):
                header_positions.append((m.start(), section_name))
        header_positions.sort()

        sections: dict[str, str] = {}
        for i, (pos, name) in enumerate(header_positions):
            end = (
                header_positions[i + 1][0]
                if i + 1 < len(header_positions)
                else len(text)
            )
            sections[name] = text[pos:end]
        return sections

    def _extract_skills(self, section_text: str) -> list[str]:
        if not section_text:
            return []
        # Remove the header line
        lines = section_text.strip().splitlines()[1:]
        skills: list[str] = []
        for line in lines:
            # Skills are often comma/bullet/pipe separated
            parts = re.split(r"[,|•·\t]", line)
            for part in parts:
                cleaned = part.strip().strip("•-–—*").strip()
                if cleaned and len(cleaned) < 50:
                    skills.append(cleaned)
        return [s for s in skills if s]

    def _extract_experience(self, section_text: str) -> list[dict]:
        if not section_text:
            return []
        entries = []
        # Split by date ranges as anchors
        parts = _DATE_RANGE_RE.split(section_text)
        i = 0
        while i < len(parts):
            block = parts[i].strip()
            if i + 2 < len(parts) and _DATE_RANGE_RE.search(parts[i] + parts[i + 1]):
                start_raw = parts[i + 1].strip() if i + 1 < len(parts) else ""
                end_raw = parts[i + 2].strip() if i + 2 < len(parts) else ""
                entry = self._parse_experience_block(block, start_raw, end_raw)
                if entry:
                    entries.append(entry)
                i += 3
            else:
                i += 1
        return entries

    def _parse_experience_block(
        self, block: str, start: str, end: str
    ) -> Optional[dict[str, Any]]:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            return None
        # Heuristic: title is usually the last meaningful line before the date
        title = lines[-1] if lines else None
        company = lines[-2] if len(lines) >= 2 else None
        return {
            "title": title,
            "company": company,
            "start": start,
            "end": end,
            "summary": " ".join(lines[:-2]) if len(lines) > 2 else None,
        }

    def _extract_education(self, section_text: str) -> list[dict]:
        if not section_text:
            return []
        entries = []
        lines = [l.strip() for l in section_text.splitlines() if l.strip()][
            1:
        ]  # skip header
        degree_re = re.compile(
            r"\b(B\.?S\.?|B\.?E\.?|B\.?Tech\.?|M\.?S\.?|M\.?Tech\.?|MBA|Ph\.?D\.?|Bachelor|Master|Doctor)\b",
            re.I,
        )
        year_re = re.compile(r"\b(19|20)\d{2}\b")
        i = 0
        while i < len(lines):
            line = lines[i]
            degree_m = degree_re.search(line)
            if degree_m:
                institution = lines[i - 1] if i > 0 else None
                year_m = year_re.search(line)
                entries.append(
                    {
                        "institution": institution,
                        "degree": degree_m.group(),
                        "field": None,  # Would need more NLP to extract
                        "end_year": year_m.group() if year_m else None,
                    }
                )
            i += 1
        return entries

    def _extract_headline(self, summary_text: str, lines: list[str]) -> Optional[str]:
        if summary_text:
            content_lines = [l.strip() for l in summary_text.splitlines() if l.strip()][
                1:3
            ]
            if content_lines:
                return " ".join(content_lines)[:200]
        # Fall back: second non-empty line after name (often the title)
        count = 0
        for line in lines[1:6]:
            stripped = line.strip()
            if stripped:
                count += 1
                if count == 1 and not _EMAIL_RE.search(stripped) and len(stripped) > 5:
                    return stripped[:200]
        return None

    def _empty(self) -> RawCandidate:
        return RawCandidate(source=SourceType.RESUME_PDF)
