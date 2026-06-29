from transformer.models.core import (
    CanonicalProfile,
    Provenance,
    SkillCanonical,
    SourceType,
)
from transformer.validator.validator import Validator


validator = Validator()


def test_valid_profile():
    profile = CanonicalProfile(
        candidate_id="cand-1",
        full_name="Jashan Singh",
        emails=["jashan@gmail.com"],
        phones=["+919876543210"],
        overall_confidence=0.9,
    )

    result = validator.validate_profile(profile)

    assert result.valid
    assert result.errors == []


def test_missing_name():
    profile = CanonicalProfile(
        candidate_id="cand-2",
        emails=["jashan@gmail.com"],
    )

    result = validator.validate_profile(profile)

    assert result.valid
    assert "Missing full_name." in result.warnings


def test_missing_email():
    profile = CanonicalProfile(
        candidate_id="cand-3",
        full_name="Jashan Singh",
        phones=["+919876543210"],
    )

    result = validator.validate_profile(profile)

    assert result.valid
    assert "Missing email." in result.warnings


def test_warning_generation():
    profile = CanonicalProfile(
        candidate_id="cand-4",
        full_name="Jashan Singh",
        emails=["not-an-email"],
        phones=["12345"],
        overall_confidence=0.8,
    )

    result = validator.validate_profile(profile)

    assert result.valid
    assert any("Invalid email format" in warning for warning in result.warnings)
    assert any("E.164" in warning for warning in result.warnings)


def test_invalid_profile():
    skill = SkillCanonical(
        name="python",
        confidence=0.9,
        sources=[SourceType.ATS_JSON.value],
    )
    skill.confidence = 1.5

    profile = CanonicalProfile(
        candidate_id="cand-5",
        full_name="Jashan Singh",
        emails=["jashan@gmail.com"],
        skills=[skill],
    )
    profile.overall_confidence = 1.5

    result = validator.validate_profile(profile)

    assert not result.valid
    assert any("overall_confidence" in error for error in result.errors)


def test_empty_profile():
    profile = CanonicalProfile(candidate_id="cand-empty")

    result = validator.validate_profile(profile)

    assert result.valid
    assert "Missing full_name." in result.warnings
    assert "Missing email." in result.warnings
