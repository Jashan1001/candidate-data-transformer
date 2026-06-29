from transformer.confidence.confidence_engine import ConfidenceEngine
from transformer.models.core import (
    CanonicalProfile,
    Provenance,
    SourceType,
)


def test_compute_confidence():
    profile = CanonicalProfile(
        candidate_id="cand-1",
        full_name="Jashan Singh",
        emails=["jashan@gmail.com"],
    )

    profile.provenance = [
        Provenance(
            field="full_name",
            source=SourceType.ATS_JSON,
            method="extracted",
            confidence=0.95,
            raw_value="Jashan Singh",
        )
    ]

    ConfidenceEngine().compute(profile)

    assert profile.overall_confidence > 0


def test_complete_profile_scores_higher():
    engine = ConfidenceEngine()

    p1 = CanonicalProfile(
        candidate_id="cand-1",
        full_name="Jashan",
    )

    p1.provenance = [
        Provenance(
            field="full_name",
            source=SourceType.ATS_JSON,
            method="extracted",
            confidence=0.95,
            raw_value="Jashan",
        )
    ]

    p2 = CanonicalProfile(
        candidate_id="cand-2",
        full_name="Jashan",
        emails=["j@gmail.com"],
        phones=["+12345678901"],
    )

    p2.provenance = [
        Provenance(
            field="full_name",
            source=SourceType.ATS_JSON,
            method="extracted",
            confidence=0.95,
            raw_value="Jashan",
        ),
        Provenance(
            field="emails",
            source=SourceType.RECRUITER_CSV,
            method="union",
            confidence=0.95,
            raw_value=["j@gmail.com"],
        ),
    ]

    engine.compute(p1)
    engine.compute(p2)

    assert p2.overall_confidence > p1.overall_confidence


def test_multiple_sources_improve_score():
    profile = CanonicalProfile(
        candidate_id="cand-3",
        full_name="Jashan",
    )

    profile.provenance = [
        Provenance(
            field="full_name",
            source=SourceType.ATS_JSON,
            method="extracted",
            confidence=0.95,
            raw_value="Jashan",
        ),
        Provenance(
            field="full_name",
            source=SourceType.RECRUITER_CSV,
            method="union",
            confidence=0.90,
            raw_value="Jashan",
        ),
    ]

    ConfidenceEngine().compute(profile)

    assert profile.overall_confidence > 0.8


def test_empty_provenance():
    profile = CanonicalProfile(candidate_id="cand-4")

    ConfidenceEngine().compute(profile)

    assert profile.overall_confidence == 0


def test_empty_profile():
    profile = CanonicalProfile(candidate_id="cand-5")

    ConfidenceEngine().compute(profile)

    assert profile.overall_confidence == 0
