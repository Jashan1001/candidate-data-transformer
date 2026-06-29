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


def test_normalize_e164_is_idempotent_on_already_normalized_value():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[FieldConfig(path="phone", from_="phones[0]", normalize="E164")],
        ),
    )
    assert output["phone"] == "+919876543210"


def test_normalize_e164_actually_reformats_a_messy_value():
    """
    The canonical model normally already stores E.164, but the projector's
    normalize="E164" should be a real, self-sufficient guarantee at the
    output boundary -- not something that only happens to work because of
    how the canonical model stores data internally. Construct a profile
    with a deliberately un-normalized phone to prove this.
    """
    profile = _profile()
    profile.phones = ["098765 43210"]  # raw-looking, no country code, no '+'

    output = Projector().project(
        profile,
        OutputConfig(
            fields=[FieldConfig(path="phone", from_="phones[0]", normalize="E164")],
        ),
    )
    assert output["phone"] == "+919876543210"


def test_normalize_canonical_collapses_skill_aliases():
    """
    Skills in the canonical model are usually already canonicalized at
    merge time, but normalize="canonical" at the projection boundary
    should hold on its own. Feed it a raw alias directly and confirm it
    gets collapsed to the canonical name.
    """
    profile = _profile()
    profile.headline = "reactjs"  # stand-in field carrying a raw skill alias

    output = Projector().project(
        profile,
        OutputConfig(
            fields=[FieldConfig(path="primary_skill", from_="headline", normalize="canonical")],
        ),
    )
    assert output["primary_skill"] == "react"


def test_normalize_iso3166_uppercases_country_code():
    output = Projector().project(
        _profile(),
        OutputConfig(
            fields=[
                FieldConfig(path="country", from_="location.country", normalize="ISO3166"),
            ],
        ),
    )
    assert output["country"] == "IN"