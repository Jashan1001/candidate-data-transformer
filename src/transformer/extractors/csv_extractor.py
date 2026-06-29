"""
Recruiter CSV extractor.

Expected columns (case-insensitive, flexible):
  name / full_name, email, phone / phone_number,
  current_company, title / job_title, location, years_experience,
  skills, linkedin_url, github_url
"""

from __future__ import annotations
import csv
import io
import re
from pathlib import Path
from typing import Any

from transformer.extractors import BaseExtractor
from transformer.models.core import RawCandidate, SourceType


# Column name aliases → canonical field
_COL_MAP = {
    "name": "full_name", "full_name": "full_name",
    "email": "email", "email_address": "email",
    "phone": "phone", "phone_number": "phone", "mobile": "phone",
    "current_company": "company", "company": "company", "employer": "company",
    "title": "title", "job_title": "title", "role": "title",
    "location": "location", "city": "location",
    "years_experience": "years_experience", "experience_years": "years_experience",
    "yoe": "years_experience",
    "skills": "skills",
    "linkedin": "linkedin_url", "linkedin_url": "linkedin_url",
    "github": "github_url", "github_url": "github_url",
    "id": "id", "candidate_id": "id",
    "headline": "headline",
}


class RecruiterCSVExtractor(BaseExtractor):
    """
    Extracts candidate records from recruiter supplied CSV files.
    """

    def extract(self, source_input: str | Path | io.StringIO) -> RawCandidate:
        """
        source_input: file path (str/Path) or a StringIO / string of CSV content.
        For multi-row CSVs (one candidate per row), returns the FIRST row only.
        To process multiple candidates, call extract_all().
        """
        rows = self._read_rows(source_input)
        if not rows:
            return self._empty()
        return self._row_to_raw(rows[0])

    def extract_all(self, source_input: str | Path | io.StringIO) -> list[RawCandidate]:
        rows = self._read_rows(source_input)
        return [self._row_to_raw(r) for r in rows]

    def _read_rows(self, source_input: str | Path | io.StringIO) -> list[dict[str, Any]]:
        if isinstance(source_input, (str, Path)):
            path = Path(source_input)
            if path.exists():
                with open(
                    path,
                    newline="",
                    encoding="utf-8-sig",
                    errors="replace",
                ) as f:
                    reader = csv.DictReader(f)
                    return [dict(r) for r in reader]
            # Might be raw CSV string
            reader = csv.DictReader(io.StringIO(str(source_input)))
            return [dict(r) for r in reader]
        elif isinstance(source_input, io.StringIO):
            source_input.seek(0)
            reader = csv.DictReader(source_input)
            return [dict(r) for r in reader]
        return []

    def _row_to_raw(self, row: dict[str, Any]) -> RawCandidate:
        mapped = self._map_columns(row)
        rc = RawCandidate(source=SourceType.RECRUITER_CSV)
        rc.raw_id = mapped.get("id")
        rc.full_name = mapped.get("full_name") or None
        email = mapped.get("email")
        if email:
            rc.emails = [e.strip() for e in re.split(r"[;,]", email) if e.strip()]
        phone = mapped.get("phone")
        if phone:
            rc.phones = [p.strip() for p in re.split(r"[;,]", phone) if p.strip()]
        rc.location_raw = mapped.get("location")
        rc.linkedin_url = mapped.get("linkedin_url")
        rc.github_url = mapped.get("github_url")
        rc.headline = mapped.get("title") or mapped.get("headline")
        rc.extra["company"] = mapped.get("company")
        yoe = mapped.get("years_experience")
        if yoe is not None and str(yoe).strip():
            try:
                rc.years_experience = float(yoe)
            except (ValueError, TypeError):
                pass
        skills_raw = mapped.get("skills", "")
        if skills_raw:
            rc.skills_raw = [s.strip() for s in re.split(r"[,;|]", skills_raw) if s.strip()]
        return rc

    def _map_columns(self, row: dict[str, Any]) -> dict[str, Any]:
        """Normalize column names and return mapped dict."""
        result: dict[str, Any] = {}
        for k, v in row.items():
            if k is None:
                continue
            norm_key = k.strip().lower().replace(" ", "_").replace("-", "_")
            canonical = _COL_MAP.get(norm_key, norm_key)
            result[canonical] = v.strip() if isinstance(v, str) else v
        return result

    def _empty(self) -> RawCandidate:
        return RawCandidate(source=SourceType.RECRUITER_CSV)