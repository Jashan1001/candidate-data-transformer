from transformer.models.config import FieldConfig, OutputConfig
from transformer.models.core import (
    CanonicalProfile,
    LocationCanonical,
    Provenance,
    SkillCanonical,
    SourceType,
)
from transformer.projector.projector import Projector


def _profile() -> CanonicalProfile:
    profile = CanonicalProfile(
        candidate_id="cand-1",
        full_name="Jashan Singh",
        emails=["jashan@gmail.com"],
        phones=["+919876543210"],
        location=LocationCanonical(city="Bangalore", country="IN"),
        skills=[
            SkillCanonical(
                name="python", confidence=0.95, sources=[SourceType.ATS_JSON.value]
            ),
        ],
        overall_confidence=0.92,
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
    return profile


def test_default_projection():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[
                FieldConfig(path="full_name"),
                FieldConfig(path="emails"),
            ],
        ),
    )

    assert output["full_name"] == "Jashan Singh"
    assert output["emails"] == ["jashan@gmail.com"]


def test_hidden_fields_omitted():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[
                FieldConfig(path="full_name"),
                FieldConfig(path="secret", from_="missing.path", on_missing="omit"),
            ],
        ),
    )

    assert "secret" not in output


def test_renamed_fields():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[
                FieldConfig(path="primary_email", from_="emails[0]"),
            ],
        ),
    )

    assert output["primary_email"] == "jashan@gmail.com"


def test_nested_projection():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[
                FieldConfig(path="contact.email", from_="emails[0]"),
                FieldConfig(path="contact.location.city", from_="location.city"),
            ],
        ),
    )

    assert output["contact"]["email"] == "jashan@gmail.com"
    assert output["contact"]["location"]["city"] == "Bangalore"


def test_provenance_inclusion():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[FieldConfig(path="full_name")],
            include_provenance=True,
        ),
    )

    assert len(output["provenance"]) == 1


def test_confidence_inclusion():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[FieldConfig(path="full_name")],
            include_confidence=True,
        ),
    )

    assert output["overall_confidence"] == 0.92
