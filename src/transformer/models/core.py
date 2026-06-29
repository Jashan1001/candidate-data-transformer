"""
Core domain models for the Multi-Source Candidate Data Transformer.

Design principles:
- FieldObservation: one raw observed value from one source
- CanonicalProfile: the single merged, normalized, trustworthy record
- Provenance: where each value came from and how confident we are
- Separation between internal canonical record and projected output
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, PrivateAttr


# ---------------------------------------------------------------------------
# Source taxonomy
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    """All supported ingestion sources. Ordered by reliability (highest first)."""
    ATS_JSON = "ats_json"           # Structured, employer-entered: highest trust
    RECRUITER_CSV = "recruiter_csv" # Structured, recruiter-entered: high trust
    RESUME_PDF = "resume_pdf"       # Candidate self-reported: medium-high trust
    RESUME_DOCX = "resume_docx"     # Candidate self-reported: medium-high trust
    GITHUB = "github"               # Public API, objective: medium trust
    RECRUITER_NOTES = "recruiter_notes"  # Free text, subjective: lower trust


# Priority order for scalar conflict resolution (index 0 = highest priority)
SOURCE_PRIORITY: list[SourceType] = [
    SourceType.ATS_JSON,
    SourceType.RECRUITER_CSV,
    SourceType.RESUME_PDF,
    SourceType.RESUME_DOCX,
    SourceType.GITHUB,
    SourceType.RECRUITER_NOTES,
]

# Base confidence weight per source (0–1)
SOURCE_BASE_CONFIDENCE: dict[SourceType, float] = {
    SourceType.ATS_JSON: 0.95,
    SourceType.RECRUITER_CSV: 0.85,
    SourceType.RESUME_PDF: 0.75,
    SourceType.RESUME_DOCX: 0.75,
    SourceType.GITHUB: 0.80,
    SourceType.RECRUITER_NOTES: 0.60,
}


# ---------------------------------------------------------------------------
# Raw extraction layer
# ---------------------------------------------------------------------------

class RawCandidate(BaseModel):
    """
    Everything a single source knows about a candidate — raw, un-normalized.
    Extraction layer produces one of these per source per candidate.
    Fields are Optional because any source may omit any field.
    """
    source: SourceType
    raw_id: Optional[str] = None

    full_name: Optional[str] = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location_raw: Optional[str] = None          # free text; normalizer parses later
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_urls: list[str] = Field(default_factory=list)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills_raw: list[str] = Field(default_factory=list)   # as extracted, pre-canonicalize
    experience_raw: list[dict[str, Any]] = Field(default_factory=list)
    education_raw: list[dict[str, Any]] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)   # source-specific overflow


# ---------------------------------------------------------------------------
# Observation — one field, one source
# ---------------------------------------------------------------------------

class FieldObservation(BaseModel):
    """
    A single observed value for a single field from a single source.
    The merger collects these per field and applies policy to pick a winner.
    """
    field: str
    value: Any
    source: SourceType
    confidence: float = Field(ge=0.0, le=1.0)
    method: str = "extracted"        # extracted | normalized | inferred | defaulted


# ---------------------------------------------------------------------------
# Canonical sub-models
# ---------------------------------------------------------------------------

class Provenance(BaseModel):
    """Lineage record attached to each field in the canonical profile."""
    field: str
    source: SourceType
    method: str
    confidence: float = Field(ge=0.0, le=1.0)
    raw_value: Optional[Any] = None  # original before normalization


class LocationCanonical(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None   # ISO-3166 alpha-2


class LinksCanonical(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


class SkillCanonical(BaseModel):
    name: str                        # canonical skill name (lowercased, normalized)
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)


class ExperienceCanonical(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None     # YYYY-MM
    end: Optional[str] = None       # YYYY-MM or null (current)
    summary: Optional[str] = None


class EducationCanonical(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[str] = None  # YYYY


# ---------------------------------------------------------------------------
# Canonical profile — the single source of truth
# ---------------------------------------------------------------------------

class CanonicalProfile(BaseModel):
    """
    The fully merged, normalized, de-duplicated candidate profile.
    This is the internal representation — never returned directly to consumers.
    The projection layer translates this to whatever shape the config requests.
    """
    candidate_id: str
    full_name: Optional[str] = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)       # E.164 format
    location: Optional[LocationCanonical] = None
    links: LinksCanonical = Field(default_factory=LinksCanonical)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: list[SkillCanonical] = Field(default_factory=list)
    experience: list[ExperienceCanonical] = Field(default_factory=list)
    education: list[EducationCanonical] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Internal: all observations before merge (useful for debugging)
    _observations: dict[str, list[FieldObservation]] = PrivateAttr(default_factory=dict)