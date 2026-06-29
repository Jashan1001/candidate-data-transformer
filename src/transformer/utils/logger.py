"""
Structured logger with coloured console output.

Usage:
    from transformer.utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Pipeline started", source="csv", candidate_id="abc")
    log.debug("Raw value", field="email", value="...", debug=True)

Set DEBUG=1 in the environment (or pass debug=True) to enable verbose logs.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# ANSI colour codes
# ---------------------------------------------------------------------------
_RESET = "\033[0m"
_BOLD = "\033[1m"
_COLOURS = {
    "DEBUG": "\033[36m",  # cyan
    "INFO": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "CRITICAL": "\033[35m",  # magenta
}

_DEBUG_MODE: bool = os.getenv("DEBUG", "").lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Custom formatter
# ---------------------------------------------------------------------------


class _StructuredFormatter(logging.Formatter):
    """
    Formats log records as coloured, human-readable lines in the console.
    Each record can carry arbitrary **kwargs stored in record.extra_fields.
    """

    def __init__(self, coloured: bool = True) -> None:
        super().__init__()
        self._coloured = coloured and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        level = record.levelname
        colour = _COLOURS.get(level, "")
        grey = "\033[90m" if self._coloured else ""
        reset = _RESET if self._coloured else ""
        colour = colour if self._coloured else ""
        bold = _BOLD if self._coloured else ""

        # Base message
        msg = record.getMessage()

        # Extra structured fields
        extra: dict[str, Any] = getattr(record, "extra_fields", {})
        suffix = ""
        if extra:
            suffix = "  " + "  ".join(f"{k}={v!r}" for k, v in extra.items())

        name = record.name.split(".")[-1]  # last segment only
        return (
            f"{colour}{bold}[{level[:4]}]{reset} "
            f"{grey}{ts}{reset} "
            f"{grey}{name}:{reset} "
            f"{msg}"
            f"{grey}{suffix}{reset}"
        )


# ---------------------------------------------------------------------------
# TransformerLogger — thin wrapper that supports structured kwargs
# ---------------------------------------------------------------------------


class TransformerLogger:
    """
    Wrapper around stdlib Logger that accepts keyword arguments as structured
    fields appended to the formatted line.

    Example:
        log.info("Extracted field", field="email", value="a@b.com")
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _log(
        self,
        level: int,
        msg: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        extra = {k: v for k, v in kwargs.items() if k != "exc_info"}
        exc_info = kwargs.get("exc_info")
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(unknown)",
            0,
            msg,
            args,
            exc_info,
        )
        record.extra_fields = extra  # type: ignore[attr-defined]
        self._logger.handle(record)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._logger.isEnabledFor(logging.DEBUG):
            self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def json_summary(self, data: dict[str, Any], label: str = "output") -> None:
        """Pretty-print a JSON dict at INFO level (useful for CLI output summary)."""
        self.info("%s:\n%s", label, json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Registry — one logger per name
# ---------------------------------------------------------------------------

_registry: dict[str, TransformerLogger] = {}


def get_logger(name: str, *, debug: bool | None = None) -> TransformerLogger:
    """
    Return (or create) a TransformerLogger for the given module name.

    Parameters
    ----------
    name : str
        Typically __name__ of the calling module.
    debug : bool | None
        Override the global DEBUG env-var for this specific logger.
        None = follow the global setting.
    """
    if name in _registry:
        return _registry[name]

    stdlib_logger = logging.getLogger(name)
    effective_debug = debug if debug is not None else _DEBUG_MODE

    if effective_debug:
        stdlib_logger.setLevel(logging.DEBUG)
    else:
        stdlib_logger.setLevel(logging.INFO)

    if not stdlib_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_StructuredFormatter(coloured=True))
        stdlib_logger.addHandler(handler)
        stdlib_logger.propagate = False

    wrapper = TransformerLogger(stdlib_logger)
    _registry[name] = wrapper
    return wrapper


def configure_root(*, debug: bool = False) -> None:
    """Call once at startup (CLI entry point) to configure root behaviour."""
    global _DEBUG_MODE  # noqa: PLW0603
    _DEBUG_MODE = debug

    root = logging.getLogger("transformer")
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_StructuredFormatter(coloured=True))
        root.addHandler(handler)
        root.propagate = False

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "requests", "pdfminer", "pdfplumber"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
