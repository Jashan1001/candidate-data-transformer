"""
Normalizer layer.

Each normalizer takes raw strings and returns clean, canonical values
plus a confidence delta. Normalizers never crash — they return (None, 0.0)
on failure so the merger can handle gracefully.
"""

from __future__ import annotations
import re
import unicodedata
from datetime import datetime
from typing import Optional

import phonenumbers

from transformer.models.core import LocationCanonical


# ---------------------------------------------------------------------------
# Phone normalization
# ---------------------------------------------------------------------------


def normalize_phone(
    raw: str, default_region: str = "IN"
) -> tuple[Optional[str], float]:
    """
    Returns (E.164 string, confidence).
    confidence=1.0 if parsed cleanly, 0.5 if valid but region-assumed.
    """
    if not raw or not raw.strip():
        return None, 0.0
    try:
        parsed = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(parsed):
            e164 = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
            # Full confidence only if country code was explicit in the raw string
            has_explicit_cc = raw.strip().startswith("+")
            return e164, 1.0 if has_explicit_cc else 0.8
        return None, 0.0
    except phonenumbers.NumberParseException:
        return None, 0.0


def normalize_phones(raws: list[str]) -> list[tuple[str, float]]:
    """Normalize a list; deduplicate by E.164 value."""
    seen: set[str] = set()
    results: list[tuple[str, float]] = []
    for r in raws:
        e164, conf = normalize_phone(r)
        if e164 and e164 not in seen:
            seen.add(e164)
            results.append((e164, conf))
    return results


# ---------------------------------------------------------------------------
# Email normalization
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def normalize_email(raw: str) -> tuple[Optional[str], float]:
    """Lowercase + strip; validate format."""
    if not raw or not raw.strip():
        return None, 0.0
    cleaned = raw.strip().lower()
    if _EMAIL_RE.fullmatch(cleaned):
        return cleaned, 1.0
    # Try to extract from noisy string
    match = _EMAIL_RE.search(raw)
    if match:
        return match.group().lower(), 0.7
    return None, 0.0


def normalize_emails(raws: list[str]) -> list[tuple[str, float]]:
    seen: set[str] = set()
    results: list[tuple[str, float]] = []
    for r in raws:
        email, conf = normalize_email(r)
        if email and email not in seen:
            seen.add(email)
            results.append((email, conf))
    return results


# ---------------------------------------------------------------------------
# Location normalization
# ---------------------------------------------------------------------------

# ISO 3166-1 alpha-2 subset — extend as needed
_COUNTRY_ALIASES: dict[str, str] = {
    "united states": "US",
    "usa": "US",
    "us": "US",
    "america": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "india": "IN",
    "canada": "CA",
    "australia": "AU",
    "germany": "DE",
    "france": "FR",
    "singapore": "SG",
    "netherlands": "NL",
    "new zealand": "NZ",
    "japan": "JP",
    "china": "CN",
}


def normalize_location(raw: str) -> tuple[Optional[LocationCanonical], float]:
    """
    Best-effort parse of free-text location.
    Handles: "San Francisco, CA, US" / "London, UK" / "Bangalore, India"
    """
    if not raw or not raw.strip():
        return None, 0.0

    parts = [p.strip() for p in raw.split(",")]
    loc = LocationCanonical()
    conf = 0.5  # base for free-text

    if len(parts) >= 3:
        loc.city = _title(parts[0])
        loc.region = parts[1]
        loc.country = _resolve_country(parts[2])
        conf = 0.9
    elif len(parts) == 2:
        loc.city = _title(parts[0])
        country_or_region = _resolve_country(parts[1])
        if country_or_region:
            loc.country = country_or_region
            conf = 0.8
        else:
            loc.region = parts[1]
            conf = 0.6
    else:
        # Single token — could be country or city
        country = _resolve_country(parts[0])
        if country:
            loc.country = country
            conf = 0.7
        else:
            loc.city = _title(parts[0])
            conf = 0.4

    return loc, conf


def _resolve_country(raw: str) -> Optional[str]:
    key = raw.strip().lower()
    # Direct 2-letter ISO code
    if re.fullmatch(r"[a-zA-Z]{2}", key):
        return key.upper()
    return _COUNTRY_ALIASES.get(key)


def _title(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).title()


# ---------------------------------------------------------------------------
# Date normalization
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m",  # 2023-06
    "%m/%Y",  # 06/2023
    "%B %Y",  # June 2023
    "%b %Y",  # Jun 2023
    "%Y",  # 2023
    "%m-%Y",  # 06-2023
    "%Y/%m",  # 2023/06
]


def normalize_date(raw: str) -> tuple[Optional[str], float]:
    """Returns (YYYY-MM, confidence)."""
    if not raw or not raw.strip():
        return None, 0.0
    raw = raw.strip()
    # "Present", "Current", "Now" → None (ongoing)
    if raw.lower() in {"present", "current", "now", "ongoing", "-"}:
        return None, 1.0
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            if fmt == "%Y":
                return f"{dt.year:04d}", 0.8  # year-only
            return f"{dt.year:04d}-{dt.month:02d}", 1.0
        except ValueError:
            continue
    return None, 0.0


# ---------------------------------------------------------------------------
# Skill canonicalization
# ---------------------------------------------------------------------------

# Maps raw skill variants → canonical name
_SKILL_CANON: dict[str, str] = {
    # Languages
    "python3": "python",
    "py": "python",
    "js": "javascript",
    "javascript": "javascript",
    "node": "node.js",
    "nodejs": "node.js",
    "ts": "typescript",
    "golang": "go",
    "c++": "c++",
    "cpp": "c++",
    "c#": "c#",
    "csharp": "c#",
    "java": "java",
    "kotlin": "kotlin",
    "swift": "swift",
    "ruby": "ruby",
    "php": "php",
    "rust": "rust",
    # Frameworks
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue.js",
    "vue": "vue.js",
    "angularjs": "angular",
    "angular": "angular",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "spring": "spring boot",
    "spring boot": "spring boot",
    "express": "express.js",
    "expressjs": "express.js",
    # Cloud & Infra
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "docker": "docker",
    # Data
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "mysql": "mysql",
    "redis": "redis",
    "kafka": "kafka",
    "elasticsearch": "elasticsearch",
    # ML/AI
    "ml": "machine learning",
    "machine learning": "machine learning",
    "dl": "deep learning",
    "deep learning": "deep learning",
    "nlp": "nlp",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    # Tools
    "git": "git",
    "github": "git",
    "gitlab": "git",
    "ci/cd": "ci/cd",
    "jenkins": "jenkins",
    "linux": "linux",
    "bash": "bash",
    "rest": "rest api",
    "rest api": "rest api",
    "graphql": "graphql",
}


def canonicalize_skill(raw: str) -> tuple[str, float]:
    """Returns (canonical_name, confidence)."""
    if not raw:
        return raw, 0.0
    cleaned = _normalize_text(raw)
    canon = _SKILL_CANON.get(cleaned)
    if canon:
        return canon, 1.0
    # Partial match: check if any known key is a substring
    for key, val in _SKILL_CANON.items():
        if key in cleaned or cleaned in key:
            return val, 0.8
    # Unknown skill — keep lowercased but note lower confidence
    return cleaned, 0.6


def canonicalize_skills(raws: list[str]) -> list[tuple[str, float]]:
    """Canonicalize + deduplicate skills."""
    seen: set[str] = set()
    results: list[tuple[str, float]] = []
    for r in raws:
        name, conf = canonicalize_skill(r)
        if name and name not in seen:
            seen.add(name)
            results.append((name, conf))
    return results


def _normalize_text(s: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower().strip())


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------


def normalize_name(raw: str) -> tuple[Optional[str], float]:
    if not raw or not raw.strip():
        return None, 0.0
    # Title-case, collapse whitespace
    cleaned = re.sub(r"\s+", " ", raw.strip())
    # Check for obviously bad values
    if len(cleaned) < 2 or re.fullmatch(r"[^a-zA-Z\s\-.']+", cleaned):
        return None, 0.2
    return cleaned.title(), 0.9
