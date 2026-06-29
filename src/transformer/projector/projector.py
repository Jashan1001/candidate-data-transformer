"""
Projection layer.

Transforms a CanonicalProfile into the output shape requested
by OutputConfig.

The projector never modifies the canonical profile.
"""

from __future__ import annotations

import re
from typing import Any

from transformer.models.config import OutputConfig
from transformer.models.core import CanonicalProfile
from transformer.normalizers import canonicalize_skill, normalize_phone
from transformer.utils.helpers import deep_get, deep_set
from transformer.utils.logger import get_logger

log = get_logger(__name__)

_E164_RE = re.compile(r"^\+\d{7,15}$")


class Projector:
    """
    Projects CanonicalProfile into arbitrary runtime JSON.
    """

    def project(
        self,
        profile: CanonicalProfile,
        config: OutputConfig,
    ) -> dict[str, Any]:

        profile_dict = profile.model_dump()

        output: dict[str, Any] = {}

        for field in config.fields:
            source_path = field.from_ or field.path

            value = deep_get(profile_dict, source_path)

            if value is None:
                action = field.on_missing or config.on_missing

                if action == "omit":
                    continue

                if action == "null":
                    deep_set(output, field.path, None)
                    continue

                if action == "error":
                    raise ValueError(f"Missing required field '{source_path}'")

            value = self._normalize(
                value,
                field.normalize,
            )

            deep_set(output, field.path, value)

        if config.include_confidence:
            output["overall_confidence"] = profile.overall_confidence

        if config.include_provenance:
            output["provenance"] = [p.model_dump() for p in profile.provenance]

        log.info(
            "Projection complete",
            fields=len(config.fields),
        )

        return output

    # ---------------------------------------------------------
    # Normalization
    #
    # Today the canonical profile already stores phones in E.164 and
    # skills under their canonical names, so these mostly act as a
    # defensive double-check at the output boundary rather than doing
    # fresh work. That matters: the canonical model storing things
    # normalized is an internal implementation detail, and the config
    # contract ("normalize": "E164") should hold regardless of how the
    # canonical model happens to store the value today. Each branch
    # below is idempotent on already-normalized input and does real
    # re-normalization if it ever receives something that isn't.
    # ---------------------------------------------------------

    def _normalize(
        self,
        value: Any,
        strategy: str | None,
    ) -> Any:

        if strategy is None or value is None:
            return value

        strategy = strategy.lower()

        if strategy == "e164":
            return self._normalize_e164(value)

        if strategy == "canonical":
            return self._normalize_canonical_skill(value)

        if strategy == "iso3166":
            return self._normalize_iso3166(value)

        log.warning("Unknown normalize strategy requested", strategy=strategy)
        return value

    def _normalize_e164(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._normalize_e164(v) for v in value]
        if not isinstance(value, str):
            return value
        if _E164_RE.fullmatch(value):
            return value  # already correct, nothing to do
        e164, _confidence = normalize_phone(value)
        if e164 is None:
            log.warning("Could not enforce E.164 on projected value", value=value)
            return value
        return e164

    def _normalize_canonical_skill(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._normalize_canonical_skill(v) for v in value]
        if not isinstance(value, str):
            return value
        canonical_name, _confidence = canonicalize_skill(value)
        return canonical_name

    def _normalize_iso3166(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._normalize_iso3166(v) for v in value]
        if not isinstance(value, str):
            return value
        upper = value.strip().upper()
        if len(upper) != 2 or not upper.isalpha():
            log.warning("Value is not a valid ISO-3166 alpha-2 code", value=value)
            return value
        return upper