"""
Main pipeline orchestrator.

Coordinates the complete transformation pipeline:

    Extract
        ↓
    Merge
        ↓
    Validate
        ↓
    Project

This module intentionally contains almost no business logic.
"""

from __future__ import annotations

from typing import Any

from transformer.extractors.ats_json_extractor import ATSJsonExtractor
from transformer.extractors.csv_extractor import RecruiterCSVExtractor
from transformer.extractors.github_extractor import GitHubExtractor

from transformer.merger.merge_engine import MergeEngine
from transformer.projector.projector import Projector
from transformer.validator.validator import Validator

from transformer.models.core import RawCandidate
from transformer.models.config import OutputConfig

from transformer.utils.logger import get_logger

log = get_logger(__name__)


class CandidateTransformer:
    """
    High-level orchestration class.

    Typical usage:

        transformer = CandidateTransformer()

        output = transformer.run(
            recruiter_csv="candidate.csv",
            ats_json="candidate.json",
            github="octocat",
            config=config,
        )
    """

    def __init__(self) -> None:

        self.csv_extractor = RecruiterCSVExtractor()
        self.ats_extractor = ATSJsonExtractor()
        self.github_extractor = GitHubExtractor()

        self.merge_engine = MergeEngine()
        self.validator = Validator()
        self.projector = Projector()

    # ----------------------------------------------------------

    def run(
        self,
        *,
        recruiter_csv: str | None = None,
        ats_json: str | None = None,
        github: str | None = None,
        config: OutputConfig,
    ) -> dict[str, Any]:

        raw_candidates: list[RawCandidate] = []

        # -------------------------------
        # Extraction
        # -------------------------------

        if recruiter_csv:
            log.info("Extracting recruiter CSV")
            raw_candidates.append(
                self.csv_extractor.safe_extract(recruiter_csv)
            )

        if ats_json:
            log.info("Extracting ATS JSON")
            raw_candidates.append(
                self.ats_extractor.safe_extract(ats_json)
            )

        if github:
            log.info("Extracting GitHub")
            raw_candidates.append(
                self.github_extractor.safe_extract(github)
            )

        if not raw_candidates:
            raise ValueError("No input sources were supplied.")

        # -------------------------------
        # Merge
        # -------------------------------

        profile = self.merge_engine.merge(raw_candidates)

        # -------------------------------
        # Validation
        # -------------------------------

        validation = self.validator.validate_profile(profile)

        if not validation.valid:

            raise ValueError(
                "\n".join(validation.errors)
            )

        if validation.warnings:
            for warning in validation.warnings:
                log.warning(warning)

        # -------------------------------
        # Projection
        # -------------------------------

        result = self.projector.project(
            profile,
            config,
        )

        log.info("Pipeline complete")

        return result