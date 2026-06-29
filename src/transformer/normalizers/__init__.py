"""
Normalization utilities.
"""

from .normalizer import (
    normalize_phone,
    normalize_phones,
    normalize_email,
    normalize_emails,
    normalize_location,
    normalize_date,
    canonicalize_skill,
    canonicalize_skills,
    normalize_name,
)

__all__ = [
    "normalize_phone",
    "normalize_phones",
    "normalize_email",
    "normalize_emails",
    "normalize_location",
    "normalize_date",
    "canonicalize_skill",
    "canonicalize_skills",
    "normalize_name",
]
