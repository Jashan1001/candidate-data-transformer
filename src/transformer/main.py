"""
Main pipeline orchestrator.

Coordinates the complete transformation pipeline:

    Extract (per source)
        ↓
    Merge (includes per-field normalization)
        ↓
    Confidence
        ↓
    Validate (canonical profile -- pre-projection sanity checks)
        ↓
    Project (apply runtime OutputConfig: select/rename/normalize fields)
        ↓
    Validate (projected output -- matches what the config actually asked for)

This module intentionally contains almost no business logic.
"""

from __future__ import annotations

from typing import Any

from transformer.extractors.ats_json_extractor import ATSJsonExtractor
from transformer.extractors.csv_extractor import RecruiterCSVExtractor
from transformer.extractors.github_extractor import GitHubExtractor
from transformer.extractors.resume_extractor import ResumeExtractor

from transformer.confidence.confidence_engine import ConfidenceEngine
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
            resume="candidate_resume.pdf",
            config=config,
        )
    """

    def __init__(self) -> None:

        self.csv_extractor = RecruiterCSVExtractor()
        self.ats_extractor = ATSJsonExtractor()
        self.github_extractor = GitHubExtractor()
        self.resume_extractor = ResumeExtractor()

        self.merge_engine = MergeEngine()
        self.confidence_engine = ConfidenceEngine()
        self.validator = Validator()
        self.projector = Projector()

    # ----------------------------------------------------------

    def run(
        self,
        *,
        recruiter_csv: str | None = None,
        ats_json: str | None = None,
        github: str | None = None,
        resume: str | None = None,
        config: OutputConfig | None = None,
    ) -> dict[str, Any]:

        if config is None:
            raise ValueError("Output config is required.")

        raw_candidates: list[RawCandidate] = []

        # -------------------------------
        # Extraction
        # -------------------------------

        if recruiter_csv:
            log.info("Extracting recruiter CSV")
            raw_candidates.append(self.csv_extractor.safe_extract(recruiter_csv))

        if ats_json:
            log.info("Extracting ATS JSON")
            raw_candidates.append(self.ats_extractor.safe_extract(ats_json))

        if github:
            log.info("Extracting GitHub")
            raw_candidates.append(self.github_extractor.safe_extract(github))

        if resume:
            log.info("Extracting resume")
            raw_candidates.append(self.resume_extractor.safe_extract(resume))

        if not raw_candidates:
            raise ValueError("No input sources were supplied.")

        # -------------------------------
        # Merge
        # -------------------------------

        profile = self.merge_engine.merge(raw_candidates)

        # -------------------------------
        # Confidence
        # -------------------------------

        log.info("Computing confidence")
        profile = self.confidence_engine.compute(profile)

        # -------------------------------
        # Validation
        # -------------------------------

        validation = self.validator.validate_profile(profile)

        if not validation.valid:
            raise ValueError("\n".join(validation.errors))

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

        # -------------------------------
        # Output validation
        #
        # The canonical profile being valid doesn't guarantee the
        # *projection* of it is -- a bad rename path, a required field
        # that on_missing quietly nulled out, or a type the config
        # promised but the data doesn't actually match. This is a
        # separate check from validate_profile() above: that one
        # protects the internal record, this one protects the contract
        # the caller's config actually asked for.
        # -------------------------------

        output_validation = self.validator.validate_output(result, config)

        if not output_validation.valid:
            raise ValueError("\n".join(output_validation.errors))

        for warning in output_validation.warnings:
            log.warning(warning)

        log.info("Pipeline complete")

        return result