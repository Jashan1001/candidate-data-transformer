"""
Utility helpers shared across the transformer pipeline.

All functions are pure, deterministic, and never raise on bad input —
they return a sensible default instead so callers remain crash-free.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Deep path helpers
# ---------------------------------------------------------------------------

_INDEX_RE = re.compile(r"^(.+?)\[(\d+)\]$")   # e.g.  phones[0]
_GLOB_RE  = re.compile(r"^(.+?)\[\]\.(.+)$")   # e.g.  skills[].name


def deep_get(obj: Any, path: str, default: Any = None) -> Any:
    """
    Retrieve a value from a nested dict/list using a dotted path string.

    Supported syntax:
        "emails"            → obj["emails"]
        "location.city"     → obj["location"]["city"]
        "phones[0]"         → obj["phones"][0]
        "skills[].name"     → [s["name"] for s in obj["skills"]]

    Returns *default* if any step in the path is missing, None, or out-of-range.

    Parameters
    ----------
    obj : Any
        The root object to traverse (usually a dict).
    path : str
        Dotted/bracketed path expression.
    default : Any
        Value returned when the path cannot be resolved.

    Examples
    --------
    >>> deep_get({"a": {"b": 1}}, "a.b")
    1
    >>> deep_get({"tags": [{"name": "python"}]}, "tags[].name")
    ['python']
    >>> deep_get({}, "missing.key", default="N/A")
    'N/A'
    """
    if obj is None:
        return default

    # List-comprehension glob: "skills[].name"
    glob_m = _GLOB_RE.match(path)
    if glob_m:
        collection_path, sub_key = glob_m.group(1), glob_m.group(2)
        collection = deep_get(obj, collection_path)
        if not isinstance(collection, list):
            return default
        return [
            value
            for item in collection
            if (value := deep_get(item, sub_key, default)) is not default
        ]

    # Walk segment by segment
    segments = _split_path(path)
    current = obj
    for seg in segments:
        if current is None:
            return default
        # Indexed access: "phones[0]"
        idx_m = _INDEX_RE.match(seg)
        if idx_m:
            key, idx = idx_m.group(1), int(idx_m.group(2))
            current = _get_key(current, key)
            if not isinstance(current, list) or idx >= len(current):
                return default
            current = current[idx]
        else:
            current = _get_key(current, seg)

    return current if current is not None else default


def _get_key(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    try:
        return getattr(obj, key)
    except AttributeError:
        return None


def _split_path(path: str) -> list[str]:
    """Split on dots that are not inside brackets."""
    segments: list[str] = []
    buf = ""
    depth = 0
    for ch in path:
        if ch == "[":
            depth += 1
            buf += ch
        elif ch == "]":
            depth -= 1
            buf += ch
        elif ch == "." and depth == 0:
            if buf:
                segments.append(buf)
            buf = ""
        else:
            buf += ch
    if buf:
        segments.append(buf)
    return segments


def deep_set(obj: dict[str, Any], path: str, value: Any) -> None:
    """
    Set a value inside a nested dict using a dotted path.
    Intermediate dicts are created automatically.
    List indexing is NOT supported (use deep_get + mutation instead).

    Parameters
    ----------
    obj : dict
        Root dict to mutate in place.
    path : str
        Dotted path, e.g. "location.city".
    value : Any
        Value to set.
    """
    segments = path.split(".")
    current = obj
    for seg in segments[:-1]:
        if seg not in current or not isinstance(current[seg], dict):
            current[seg] = {}
        current = current[seg]
    current[segments[-1]] = value


# ---------------------------------------------------------------------------
# Dict utilities
# ---------------------------------------------------------------------------

def flatten_dict(
    obj: dict[str, Any],
    *,
    sep: str = ".",
    prefix: str = "",
) -> dict[str, Any]:
    """
    Flatten a nested dict into a single-level dict with dotted keys.

    Parameters
    ----------
    obj : dict
        The dict to flatten.
    sep : str
        Separator character between key levels (default ".").
    prefix : str
        Prefix to prepend to all keys (used for recursion).

    Examples
    --------
    >>> flatten_dict({"a": {"b": 1, "c": 2}, "d": 3})
    {'a.b': 1, 'a.c': 2, 'd': 3}
    """
    result: dict[str, Any] = {}
    for k, v in obj.items():
        full_key = f"{prefix}{sep}{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten_dict(v, sep=sep, prefix=full_key))
        else:
            result[full_key] = v
    return result


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(items: list[Any], *, key: str | None = None) -> list[Any]:
    """
    Remove duplicates from a list, preserving order of first occurrence.

    Parameters
    ----------
    items : list
        The list to deduplicate.
    key : str | None
        If provided, items are assumed to be dicts/objects and this attribute
        is used as the dedup key. If None, items are compared by value.

    Examples
    --------
    >>> deduplicate([3, 1, 2, 1, 3])
    [3, 1, 2]
    >>> deduplicate([{"name": "a"}, {"name": "b"}, {"name": "a"}], key="name")
    [{'name': 'a'}, {'name': 'b'}]
    """
    seen: set[Any] = set()
    result: list[Any] = []
    for item in items:
        fingerprint: Any
        if key is not None:
            fingerprint = item.get(key) if isinstance(item, dict) else getattr(item, key, item)
        else:
            try:
                fingerprint = item
                hash(item)  # test hashability
            except TypeError:
                fingerprint = json.dumps(item, sort_keys=True, default=str)
        if fingerprint not in seen:
            seen.add(fingerprint)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Safe coercion
# ---------------------------------------------------------------------------

def safe_float(val: Any, *, default: float | None = None) -> float | None:
    """
    Convert *val* to float without raising.

    Returns *default* (None by default) if conversion fails or val is falsy.

    Examples
    --------
    >>> safe_float("3.5")
    3.5
    >>> safe_float("n/a") is None
    True
    >>> safe_float(None, default=0.0)
    0.0
    """
    if val is None:
        return default
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def safe_list(val: Any) -> list[Any]:
    """
    Always return a list.

    - list → returned as-is
    - None / empty string → []
    - anything else → [val]

    Examples
    --------
    >>> safe_list(None)
    []
    >>> safe_list("hello")
    ['hello']
    >>> safe_list([1, 2])
    [1, 2]
    """
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, (str, bytes)) and not val:
        return []
    return [val]


# ---------------------------------------------------------------------------
# Identity / UUID
# ---------------------------------------------------------------------------

def generate_candidate_id(
    *,
    email: str | None = None,
    name: str | None = None,
    raw_id: str | None = None,
) -> str:
    """
    Generate a stable, deterministic candidate ID.

    Preference order: raw_id from ATS → email-based → name-based → random UUID.
    The email-based ID uses UUID5 (namespace + email) for reproducibility.

    Parameters
    ----------
    email : str | None
        Primary email address of the candidate.
    name : str | None
        Full name of the candidate (fallback).
    raw_id : str | None
        Existing ATS/system identifier (highest priority).

    Returns
    -------
    str
        A non-empty string identifier.
    """
    if raw_id and raw_id.strip():
        return raw_id.strip()
    if email and email.strip():
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, email.strip().lower()))
    if name and name.strip():
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, name.strip().lower()))
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------

def ensure_parent(path: str | Path) -> Path:
    """
    Ensure the parent directory of *path* exists (creates it if needed).
    Returns a resolved Path object.
    """
    p = Path(path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def with_suffix(path: str | Path, suffix: str) -> Path:
    """Return *path* with the given suffix, replacing any existing one."""
    return Path(path).with_suffix(suffix)


# ---------------------------------------------------------------------------
# Iterable helpers
# ---------------------------------------------------------------------------

def chunked(iterable: list[Any], size: int) -> Iterator[list[Any]]:
    """
    Yield successive chunks of *size* from *iterable*.

    Examples
    --------
    >>> list(chunked([1,2,3,4,5], 2))
    [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]
