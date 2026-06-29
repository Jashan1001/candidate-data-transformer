"""
Projection layer.

Transforms a CanonicalProfile into the output shape requested
by OutputConfig.

The projector never modifies the canonical profile.
"""

from __future__ import annotations

from typing import Any

from transformer.models.config import OutputConfig
from transformer.models.core import CanonicalProfile
from transformer.utils.helpers import deep_get, deep_set
from transformer.utils.logger import get_logger

log = get_logger(__name__)


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
                    raise ValueError(
                        f"Missing required field '{source_path}'"
                    )

            value = self._normalize(
                value,
                field.normalize,
            )

            deep_set(output, field.path, value)

        if config.include_confidence:
            output["overall_confidence"] = profile.overall_confidence

        if config.include_provenance:
            output["provenance"] = [
                p.model_dump()
                for p in profile.provenance
            ]

        log.info(
            "Projection complete",
            fields=len(config.fields),
        )

        return output

    # ---------------------------------------------------------

    def _normalize(
        self,
        value: Any,
        strategy: str | None,
    ) -> Any:

        if strategy is None:
            return value

        if strategy.lower() == "canonical":
            return value

        if strategy.lower() == "e164":
            return value

        if strategy.lower() == "iso3166":
            return value

        return value