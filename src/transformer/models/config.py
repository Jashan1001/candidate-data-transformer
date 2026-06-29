"""
Runtime output configuration model.

Allows callers to reshape the canonical output at query time:
- select a subset of fields
- rename / remap a field via 'from' path
- apply per-field normalization
- toggle provenance and confidence inclusion
- control missing-value behaviour
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


class FieldConfig(BaseModel):
    path: str  # output key name
    from_: Optional[str] = Field(None, alias="from")  # source path in canonical model
    type: Optional[
        Literal[
            "string",
            "string[]",
            "number",
            "boolean",
            "object",
        ]
    ] = None  # string | string[] | number | etc.
    required: bool = False
    normalize: Optional[
        Literal[
            "E164",
            "canonical",
            "ISO3166",
        ]
    ] = None  # "E164" | "canonical" | "ISO3166" | None
    on_missing: Optional[Literal["null", "omit", "error"]] = (
        None  # field-level override
    )

    model_config = {"populate_by_name": True}


class OutputConfig(BaseModel):
    """
    Full runtime config.

    Example:
    {
      "fields": [
        {"path": "full_name", "type": "string", "required": true},
        {"path": "primary_email", "from": "emails[0]", "type": "string"},
        {"path": "phone", "from": "phones[0]", "normalize": "E164"},
        {"path": "skills", "from": "skills[].name", "type": "string[]"}
      ],
      "include_confidence": true,
      "include_provenance": false,
      "on_missing": "null"
    }
    """

    fields: list[FieldConfig] = Field(default_factory=list)
    include_confidence: bool = True
    include_provenance: bool = False
    on_missing: Literal["null", "omit", "error"] = "null"
