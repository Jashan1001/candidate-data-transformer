import pytest

from transformer.merger.merge_engine import MergeEngine
from transformer.models.core import RawCandidate, SourceType


def test_merge_basic_fields():
    csv = RawCandidate(
        source=SourceType.RECRUITER_CSV,
        full_name="Jashan Singh",
        emails=["jashan@gmail.com"],
    )

    ats = RawCandidate(
        source=SourceType.ATS_JSON,
        full_name="Jashan Singh",
        phones=["+919876543210"],
    )

    profile = MergeEngine().merge([csv, ats])

    assert profile.full_name == "Jashan Singh"
    assert profile.emails == ["jashan@gmail.com"]
    assert profile.phones == ["+919876543210"]


def test_email_deduplication():
    c1 = RawCandidate(
        source=SourceType.RECRUITER_CSV,
        emails=["jashan@gmail.com"],
    )

    c2 = RawCandidate(
        source=SourceType.ATS_JSON,
        emails=["jashan@gmail.com"],
    )

    profile = MergeEngine().merge([c1, c2])

    assert profile.emails == ["jashan@gmail.com"]


def test_phone_deduplication():
    c1 = RawCandidate(
        source=SourceType.RECRUITER_CSV,
        phones=["+919876543210"],
    )

    c2 = RawCandidate(
        source=SourceType.ATS_JSON,
        phones=["+919876543210"],
    )

    profile = MergeEngine().merge([c1, c2])

    assert len(profile.phones) == 1


def test_skill_union():
    c1 = RawCandidate(
        source=SourceType.RECRUITER_CSV,
        skills_raw=["Python", "Docker"],
    )

    c2 = RawCandidate(
        source=SourceType.ATS_JSON,
        skills_raw=["Docker", "Redis"],
    )

    profile = MergeEngine().merge([c1, c2])

    names = {s.name for s in profile.skills}

    assert names == {
        "python",
        "docker",
        "redis",
    }


def test_years_experience():
    c1 = RawCandidate(
        source=SourceType.RECRUITER_CSV,
        years_experience=3,
    )

    profile = MergeEngine().merge([c1])

    assert profile.years_experience == 3


def test_provenance_exists():
    c1 = RawCandidate(
        source=SourceType.RECRUITER_CSV,
        full_name="Jashan Singh",
    )

    profile = MergeEngine().merge([c1])

    assert len(profile.provenance) > 0


def test_empty_merge():
    profile = MergeEngine().merge([])

    assert profile.candidate_id is not None
    assert profile.full_name is None
    assert profile.emails == []


def test_candidate_id_exists():
    c1 = RawCandidate(
        source=SourceType.RECRUITER_CSV,
        full_name="Jashan Singh",
    )

    profile = MergeEngine().merge([c1])

    assert profile.candidate_id is not None
