import io

from transformer.extractors.csv_extractor import RecruiterCSVExtractor
from transformer.models.core import SourceType


def test_extract_single_candidate():
    csv_data = io.StringIO(
        """name,email,phone,skills,years_experience
Jashan Singh,jashan@gmail.com,+919876543210,"Python,Docker",3
"""
    )

    extractor = RecruiterCSVExtractor()

    candidate = extractor.extract(csv_data)

    assert candidate.source == SourceType.RECRUITER_CSV
    assert candidate.full_name == "Jashan Singh"
    assert candidate.emails == ["jashan@gmail.com"]
    assert candidate.phones == ["+919876543210"]
    assert candidate.skills_raw == ["Python", "Docker"]
    assert candidate.years_experience == 3.0


def test_extract_all_candidates():
    csv_data = io.StringIO(
        """name,email
Alice,alice@gmail.com
Bob,bob@gmail.com
"""
    )

    extractor = RecruiterCSVExtractor()

    candidates = extractor.extract_all(csv_data)

    assert len(candidates) == 2
    assert candidates[0].full_name == "Alice"
    assert candidates[1].full_name == "Bob"


def test_missing_optional_columns():
    csv_data = io.StringIO(
        """name,email
Jashan,jashan@gmail.com
"""
    )

    extractor = RecruiterCSVExtractor()

    candidate = extractor.extract(csv_data)

    assert candidate.full_name == "Jashan"
    assert candidate.location_raw is None
    assert candidate.skills_raw == []


def test_multiple_emails():
    csv_data = io.StringIO(
        """name,email
Jashan,"a@gmail.com;b@gmail.com"
"""
    )

    extractor = RecruiterCSVExtractor()

    candidate = extractor.extract(csv_data)

    assert candidate.emails == [
        "a@gmail.com",
        "b@gmail.com",
    ]


def test_multiple_phones():
    csv_data = io.StringIO(
        """name,phone
Jashan,"1111111111;2222222222"
"""
    )

    extractor = RecruiterCSVExtractor()

    candidate = extractor.extract(csv_data)

    assert len(candidate.phones) == 2


def test_skill_parsing():
    csv_data = io.StringIO(
        """name,skills
Jashan,"Python;Docker|Redis,C++"
"""
    )

    extractor = RecruiterCSVExtractor()

    candidate = extractor.extract(csv_data)

    assert candidate.skills_raw == [
        "Python",
        "Docker",
        "Redis",
        "C++",
    ]


def test_invalid_years_experience():
    csv_data = io.StringIO(
        """name,years_experience
Jashan,abc
"""
    )

    extractor = RecruiterCSVExtractor()

    candidate = extractor.extract(csv_data)

    assert candidate.years_experience is None
