from transformer.models.core import (
    CanonicalProfile,
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


def test_validate_output_required_field_missing_is_an_error():
    from transformer.models.config import FieldConfig, OutputConfig

    output = {"full_name": None}
    config = OutputConfig(
        fields=[FieldConfig(path="full_name", required=True)],
    )

    result = validator.validate_output(output, config)

    assert not result.valid
    assert any("full_name" in error for error in result.errors)


def test_validate_output_type_mismatch_is_an_error():
    from transformer.models.config import FieldConfig, OutputConfig

    output = {"years_experience": "three"}  # should be a number
    config = OutputConfig(
        fields=[FieldConfig(path="years_experience", type="number")],
    )

    result = validator.validate_output(output, config)

    assert not result.valid
    assert any("years_experience" in error for error in result.errors)


def test_validate_output_string_array_type_check():
    from transformer.models.config import FieldConfig, OutputConfig

    good = {"skills": ["python", "docker"]}
    bad = {"skills": [{"name": "python"}]}
    config = OutputConfig(
        fields=[FieldConfig(path="skills", type="string[]")],
    )

    assert validator.validate_output(good, config).valid
    assert not validator.validate_output(bad, config).valid


def test_validate_output_passes_when_everything_matches():
    from transformer.models.config import FieldConfig, OutputConfig

    output = {"full_name": "Jordan Reyes", "years_experience": 3}
    config = OutputConfig(
        fields=[
            FieldConfig(path="full_name", type="string", required=True),
            FieldConfig(path="years_experience", type="number"),
        ],
    )

    result = validator.validate_output(output, config)
    assert result.valid
    assert result.errors == []