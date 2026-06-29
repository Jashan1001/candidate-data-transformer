from transformer.extractors.ats_json_extractor import ATSJsonExtractor
from transformer.models.core import SourceType


def test_greenhouse_candidate():
    data = {
        "id": 1,
        "candidate": {
            "name": "Jashanpreet Kaur",
            "email_addresses": [
                {"value": "jashanpreet@gmail.com"}
            ],
            "phone_numbers": [
                {"value": "+919876543210"}
            ],
            "location": {
                "name": "Bangalore"
            },
            "tags": [
                {"name": "Python"},
                {"name": "Docker"},
            ],
        }
    }

    extractor = ATSJsonExtractor()

    candidate = extractor.extract(data)

    assert candidate.source == SourceType.ATS_JSON
    assert candidate.full_name == "Jashanpreet Kaur"
    assert candidate.emails == ["jashanpreet@gmail.com"]
    assert candidate.phones == ["+919876543210"]
    assert candidate.location_raw == "Bangalore"
    assert candidate.skills_raw == ["Python", "Docker"]


def test_lever_candidate():
    data = {
        "id": 5,
        "name": "Jashanpreet Kaur",
        "emails": [
            {"value": "jashanpreet@gmail.com"}
        ],
        "phones": [
            {"value": "+919876543210"}
        ],
        "tags": [
            "Python",
            "Redis"
        ]
    }

    extractor = ATSJsonExtractor()

    candidate = extractor.extract(data)

    assert candidate.full_name == "Jashanpreet Kaur"
    assert candidate.emails == ["jashanpreet@gmail.com"]
    assert candidate.phones == ["+919876543210"]
    assert candidate.skills_raw == ["Python", "Redis"]


def test_generic_candidate():
    data = {
        "full_name": "Jashanpreet Kaur",
        "email": "jashanpreet@gmail.com",
        "phone": "+919876543210",
        "skills": [
            "Python",
            "Docker",
        ],
    }

    extractor = ATSJsonExtractor()

    candidate = extractor.extract(data)

    assert candidate.full_name == "Jashanpreet Kaur"
    assert candidate.emails == ["jashanpreet@gmail.com"]
    assert candidate.phones == ["+919876543210"]
    assert candidate.skills_raw == ["Python", "Docker"]


def test_missing_fields():
    extractor = ATSJsonExtractor()

    candidate = extractor.extract({})

    assert candidate.source == SourceType.ATS_JSON
    assert candidate.full_name is None
    assert candidate.emails == []


def test_email_dict():
    data = {
        "emails": [
            {"email": "abc@gmail.com"}
        ]
    }

    extractor = ATSJsonExtractor()

    candidate = extractor.extract(data)

    assert candidate.emails == ["abc@gmail.com"]


def test_phone_dict():
    data = {
        "phones": [
            {"phone": "+919999999999"}
        ]
    }

    extractor = ATSJsonExtractor()

    candidate = extractor.extract(data)

    assert candidate.phones == ["+919999999999"]


def test_tags_to_skills():
    data = {
        "tags": [
            {"name": "Kafka"},
            {"name": "Redis"},
        ]
    }

    extractor = ATSJsonExtractor()

    candidate = extractor.extract(data)

    assert candidate.skills_raw == [
        "Kafka",
        "Redis",
    ]


def test_invalid_experience():
    data = {
        "years_experience": "abc"
    }

    extractor = ATSJsonExtractor()

    candidate = extractor.extract(data)

    assert candidate.years_experience is None


def test_generic_payload_with_plain_emails_key_keeps_skills():
    """
    Regression test for a real bug found while reviewing the sample fixture:
    a generic-shaped ATS payload (plain "skills" list, no "tags", no
    "applications") was being misrouted into the Lever-flavor parser just
    because it happened to have a top-level "emails" key -- a field name
    plenty of non-Lever exports also use. The Lever parser reads skills
    from "tags", not "skills", so skills were silently dropped.

    "emails" alone must NOT trigger Lever parsing, and even if a flavor
    guess is ever wrong again, the fallback safety net in extract() must
    still recover a clearly-present top-level "skills" key.
    """
    data = {
        "id": "123",
        "name": "Jordan Reyes",
        "emails": ["jordan@example.com"],
        "phones": ["+15555550123"],
        "skills": ["Python", "Docker", "Kafka"],
        "years_experience": 3,
    }

    extractor = ATSJsonExtractor()
    candidate = extractor.extract(data)

    assert set(candidate.skills_raw) == {"Python", "Docker", "Kafka"}
    assert candidate.full_name == "Jordan Reyes"
    assert candidate.emails == ["jordan@example.com"]