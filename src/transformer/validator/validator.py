"""
Validation layer.

Responsible for validating both:
1. Canonical candidate profiles.
2. Runtime output configuration.

Validation never raises unexpectedly. Instead it returns structured
errors and warnings so the pipeline can decide whether to continue.
"""

from __future__ import annotations

import re
from typing import Any

from transformer.models.config import OutputConfig
from transformer.models.core import CanonicalProfile
from transformer.utils.helpers import deep_get
from transformer.utils.logger import get_logger

log = get_logger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_PHONE_RE = re.compile(r"^\+\d{7,15}$")


class ValidationResult:
    """
    Holds validation output.

    valid:
        True only if no errors were found.

    errors:
        Problems that should stop projection.

    warnings:
        Non-fatal issues.
    """

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class Validator:
    """
    Validates CanonicalProfile and OutputConfig.
    """

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def validate_profile(
        self,
        profile: CanonicalProfile,
    ) -> ValidationResult:

        result = ValidationResult()

        self._validate_required(profile, result)
        self._validate_emails(profile, result)
        self._validate_phones(profile, result)
        self._validate_confidence(profile, result)

        log.info(
            "Profile validation complete",
            valid=result.valid,
            errors=len(result.errors),
            warnings=len(result.warnings),
        )

        return result

    def validate_config(
        self,
        config: OutputConfig,
        profile: CanonicalProfile | None = None,
    ) -> ValidationResult:

        result = ValidationResult()

        for field in config.fields:
            if not field.path:
                result.add_error("Field path cannot be empty.")

            if profile is not None and field.from_:
                value = deep_get(profile.model_dump(), field.from_)
                if value is None:
                    result.add_warning(f"Field '{field.from_}' does not exist.")

        return result

    def validate_output(
        self,
        output: dict,
        config: OutputConfig,
    ) -> ValidationResult:
        """
        Validate the FINAL projected JSON against what the config actually
        asked for. This runs after Projector.project(), not before -- the
        canonical profile can be perfectly valid while the *projection* of
        it is still wrong (a bad rename path, a type mismatch the config
        declared, or a required field that on_missing quietly nulled out).

        Two things checked per field:
        1. required: True must mean the field is actually present and
           non-null in the output, regardless of what on_missing said to
           do at projection time. (Previously `required` was accepted by
           the config schema but never enforced anywhere.)
        2. type: if declared, the projected value's Python type must
           match what was promised (string, string[], number, boolean,
           object), so a config can't silently claim one shape and
           deliver another.
        """
        result = ValidationResult()

        for field in config.fields:
            value = deep_get(output, field.path)

            if field.required and value is None:
                result.add_error(
                    f"Required field '{field.path}' is missing from the output."
                )
                continue

            if value is None:
                continue

            if field.type and not self._matches_declared_type(value, field.type):
                result.add_error(
                    f"Field '{field.path}' does not match declared type "
                    f"'{field.type}' (got {type(value).__name__})."
                )

        log.info(
            "Output validation complete",
            valid=result.valid,
            errors=len(result.errors),
        )

        return result

    @staticmethod
    def _matches_declared_type(value: Any, declared_type: str) -> bool:
        if declared_type == "string":
            return isinstance(value, str)
        if declared_type == "string[]":
            return isinstance(value, list) and all(isinstance(v, str) for v in value)
        if declared_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if declared_type == "boolean":
            return isinstance(value, bool)
        if declared_type == "object":
            return isinstance(value, dict)
        return True  # unrecognized declared type -- don't fail on it

    # ---------------------------------------------------------
    # Internal validation
    # ---------------------------------------------------------

    def _validate_required(
        self,
        profile: CanonicalProfile,
        result: ValidationResult,
    ) -> None:

        if not profile.full_name:
            result.add_warning("Missing full_name.")

        if not profile.emails:
            result.add_warning("Missing email.")

    def _validate_emails(
        self,
        profile: CanonicalProfile,
        result: ValidationResult,
    ) -> None:

        for email in profile.emails:
            if not _EMAIL_RE.fullmatch(email):
                result.add_warning(f"Invalid email format: {email}")

    def _validate_phones(
        self,
        profile: CanonicalProfile,
        result: ValidationResult,
    ) -> None:

        for phone in profile.phones:
            if not _PHONE_RE.fullmatch(phone):
                result.add_warning(f"Phone is not valid E.164: {phone}")

    def _validate_confidence(
        self,
        profile: CanonicalProfile,
        result: ValidationResult,
    ) -> None:

        if not (0.0 <= profile.overall_confidence <= 1.0):
            result.add_error("overall_confidence must be between 0 and 1.")

        for skill in profile.skills:
            if not (0.0 <= skill.confidence <= 1.0):
                result.add_error(f"Invalid confidence for skill '{skill.name}'.")