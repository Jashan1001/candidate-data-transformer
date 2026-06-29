import json
from unittest.mock import Mock

import pytest

from transformer.extractors.github_extractor import GitHubExtractor
from transformer.main import CandidateTransformer
from transformer.models.config import FieldConfig, OutputConfig


def _output_config() -> OutputConfig:
    return OutputConfig(
        fields=[
            FieldConfig(path="full_name"),
            FieldConfig(path="emails"),
            FieldConfig(path="phones"),
            FieldConfig(path="years_experience"),
            FieldConfig(path="skills", from_="skills[].name", type="string[]"),
            FieldConfig(path="github_url", from_="links.github"),
        ],
        include_confidence=True,
        include_provenance=True,
    )


def _write_csv(tmp_path, content: str):
    csv_file = tmp_path / "candidate.csv"
    csv_file.write_text(content, encoding="utf-8")
    return csv_file


def _write_ats(tmp_path, payload: dict):
    ats_file = tmp_path / "candidate.json"
    ats_file.write_text(json.dumps(payload), encoding="utf-8")
    return ats_file


def _mocked_github_extractor() -> GitHubExtractor:
    session = Mock()

    profile_response = Mock()
    profile_response.ok = True
    profile_response.status_code = 200
    profile_response.headers = {"X-RateLimit-Remaining": "10"}
    profile_response.json.return_value = {
        "id": 1,
        "name": "Jashan Singh",
        "html_url": "https://github.com/Jashan1001",
        "bio": "Software Engineer",
        "location": "Bangalore",
        "company": "@OpenAI",
        "followers": 10,
        "following": 5,
    }

    repo_response = Mock()
    repo_response.ok = True
    repo_response.status_code = 200
    repo_response.headers = {"X-RateLimit-Remaining": "10"}
    repo_response.json.return_value = [
        {
            "fork": False,
            "name": "candidate-data-utils",
            "language": "Python",
            "topics": ["fastapi"],
            "stargazers_count": 10,
            "forks_count": 2,
        },
        {
            "fork": False,
            "name": "infra",
            "language": "Dockerfile",
            "topics": ["deploy"],
            "stargazers_count": 4,
            "forks_count": 1,
        },
    ]

    session.get.side_effect = [profile_response, repo_response]
    return GitHubExtractor(session=session)


def test_pipeline_csv_and_ats(tmp_path):
    csv_file = _write_csv(
        tmp_path,
        """name,email,phone,skills\nJashan Singh,jashan@gmail.com,+919876543210,Python;Docker\n""",
    )
    ats_file = _write_ats(
        tmp_path,
        {
            "id": 1,
            "candidate": {
                "name": "Jashan Singh",
                "email_addresses": [{"value": "jashan@gmail.com"}],
                "phone_numbers": [{"value": "+919876543210"}],
                "tags": [{"name": "Redis"}],
            },
        },
    )

    transformer = CandidateTransformer()

    result = transformer.run(
        recruiter_csv=str(csv_file),
        ats_json=str(ats_file),
        config=_output_config(),
    )

    assert result["full_name"] == "Jashan Singh"
    assert result["emails"] == ["jashan@gmail.com"]
    assert result["phones"] == ["+919876543210"]
    assert set(result["skills"]) == {"python", "docker", "redis"}
    assert result["overall_confidence"] > 0
    assert len(result["provenance"]) > 0


def test_pipeline_csv_only(tmp_path):
    csv_file = _write_csv(
        tmp_path,
        """name,email,phone,skills\nJashan Singh,jashan@gmail.com,+919876543210,Python\n""",
    )

    transformer = CandidateTransformer()

    result = transformer.run(
        recruiter_csv=str(csv_file),
        config=_output_config(),
    )

    assert result["full_name"] == "Jashan Singh"
    assert result["emails"] == ["jashan@gmail.com"]
    assert result["overall_confidence"] > 0


def test_pipeline_ats_only(tmp_path):
    ats_file = _write_ats(
        tmp_path,
        {
            "full_name": "Jashan Singh",
            "email": "jashan@gmail.com",
            "phone": "+919876543210",
            "skills": ["Python", "Redis"],
            "years_experience": 3,
        },
    )

    transformer = CandidateTransformer()

    result = transformer.run(
        ats_json=str(ats_file),
        config=_output_config(),
    )

    assert result["full_name"] == "Jashan Singh"
    assert result["years_experience"] == 3.0
    assert result["overall_confidence"] > 0


def test_pipeline_full_with_mocked_github(tmp_path):
    csv_file = _write_csv(
        tmp_path,
        """name,email,phone,skills\nJashan Singh,jashan@gmail.com,+919876543210,Python;Docker\n""",
    )
    ats_file = _write_ats(
        tmp_path,
        {
            "id": 1,
            "candidate": {
                "name": "Jashan Singh",
                "phone_numbers": [{"value": "+919876543210"}],
                "tags": [{"name": "Redis"}],
            },
        },
    )

    transformer = CandidateTransformer()
    transformer.github_extractor = _mocked_github_extractor()

    result = transformer.run(
        recruiter_csv=str(csv_file),
        ats_json=str(ats_file),
        github="Jashan1001",
        config=_output_config(),
    )

    required = {
        "full_name",
        "emails",
        "overall_confidence",
        "provenance",
    }

    assert isinstance(result, dict)
    assert required.issubset(result.keys())
    assert result["full_name"] == "Jashan Singh"
    assert result["github_url"] == "https://github.com/Jashan1001"
    assert "fastapi" in result["skills"]
    assert any(p["source"] == "github" for p in result["provenance"])


def test_pipeline_missing_config(tmp_path):
    csv_file = _write_csv(
        tmp_path,
        """name,email\nJashan Singh,jashan@gmail.com\n""",
    )

    transformer = CandidateTransformer()

    with pytest.raises(ValueError, match="Output config is required"):
        transformer.run(recruiter_csv=str(csv_file))


def test_invalid_csv(tmp_path, monkeypatch):
    csv_file = _write_csv(
        tmp_path,
        "name,email\nJashan Singh,jashan@gmail.com\n",
    )

    transformer = CandidateTransformer()
    monkeypatch.setattr(
        transformer.csv_extractor,
        "extract",
        Mock(side_effect=ValueError("bad csv")),
    )

    result = transformer.run(
        recruiter_csv=str(csv_file),
        config=_output_config(),
    )

    assert result["full_name"] is None
    assert result["emails"] == []
    assert result["overall_confidence"] == 0.0


def test_invalid_ats(tmp_path):
    ats_file = tmp_path / "candidate.json"
    ats_file.write_text('{"full_name": "Jashan Singh",', encoding="utf-8")

    transformer = CandidateTransformer()

    result = transformer.run(
        ats_json=str(ats_file),
        config=_output_config(),
    )

    assert result["full_name"] is None
    assert result["emails"] == []
    assert result["overall_confidence"] == 0.0


def test_pipeline_no_input():
    transformer = CandidateTransformer()

    with pytest.raises(ValueError, match="No input sources were supplied"):
        transformer.run(config=_output_config())
