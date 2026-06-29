from transformer.normalizers import (
    normalize_phone,
    normalize_phones,
    normalize_email,
    normalize_emails,
    normalize_location,
    normalize_date,
    canonicalize_skill,
    canonicalize_skills,
    normalize_name,
)


def test_normalize_valid_indian_phone():
    phone, confidence = normalize_phone("+919876543210")

    assert phone == "+919876543210"
    assert confidence == 1.0


def test_normalize_phone_without_country_code():
    phone, confidence = normalize_phone("9876543210")

    assert phone == "+919876543210"
    assert confidence == 0.8


def test_invalid_phone_returns_none():
    phone, confidence = normalize_phone("12345")

    assert phone is None
    assert confidence == 0.0


def test_normalize_phones_removes_duplicates():
    phones = normalize_phones(
        [
            "+919876543210",
            "9876543210",
        ]
    )

    assert len(phones) == 1
    assert phones[0][0] == "+919876543210"


def test_normalize_email_lowercase():
    email, confidence = normalize_email("JASHAN@GMAIL.COM")

    assert email == "jashan@gmail.com"
    assert confidence == 1.0


def test_extract_email_from_text():
    email, confidence = normalize_email("Contact me at jashan@gmail.com for details.")

    assert email == "jashan@gmail.com"
    assert confidence == 0.7


def test_invalid_email():
    email, confidence = normalize_email("not-an-email")

    assert email is None
    assert confidence == 0.0


def test_normalize_emails_removes_duplicates():
    emails = normalize_emails(
        [
            "JASHAN@gmail.com",
            "jashan@gmail.com",
        ]
    )

    assert len(emails) == 1
    assert emails[0][0] == "jashan@gmail.com"


def test_python3_becomes_python():
    skill, confidence = canonicalize_skill("Python3")

    assert skill == "python"
    assert confidence == 1.0


def test_cpp_becomes_cplusplus():
    skill, confidence = canonicalize_skill("CPP")

    assert skill == "c++"
    assert confidence >= 0.8


def test_reactjs_becomes_react():
    skill, confidence = canonicalize_skill("ReactJS")

    assert skill == "react"
    assert confidence == 1.0


def test_unknown_skill():
    skill, confidence = canonicalize_skill("SomeRandomSkill")

    assert skill == "somerandomskill"
    assert confidence == 0.6


def test_duplicate_skills_removed():
    skills = canonicalize_skills(
        [
            "Python3",
            "python",
            "PY",
        ]
    )

    assert len(skills) == 1


def test_bangalore_location():
    location, confidence = normalize_location("Bangalore, India")

    assert location is not None
    assert location.city == "Bangalore"
    assert location.country == "IN"
    assert confidence == 0.8


def test_country_only():
    location, confidence = normalize_location("India")

    assert location is not None
    assert location.country == "IN"
    assert confidence == 0.7


def test_three_part_location():
    location, confidence = normalize_location("San Francisco, CA, US")

    assert location is not None
    assert location.city == "San Francisco"
    assert location.region == "CA"
    assert location.country == "US"
    assert confidence == 0.9


def test_empty_location():
    location, confidence = normalize_location("")

    assert location is None
    assert confidence == 0.0


def test_month_year():
    date, confidence = normalize_date("Jun 2023")

    assert date == "2023-06"
    assert confidence == 1.0


def test_numeric_month():
    date, confidence = normalize_date("06/2023")

    assert date == "2023-06"


def test_year_only():
    date, confidence = normalize_date("2023")

    assert date == "2023"
    assert confidence == 0.8


def test_present():
    date, confidence = normalize_date("Present")

    assert date is None
    assert confidence == 1.0


def test_invalid_date():
    date, confidence = normalize_date("abcdef")

    assert date is None
    assert confidence == 0.0


def test_name_title_case():
    name, confidence = normalize_name("jashan singh")

    assert name == "Jashan Singh"
    assert confidence == 0.9


def test_name_extra_spaces():
    name, confidence = normalize_name("   jashan     singh   ")

    assert name == "Jashan Singh"


def test_invalid_name():
    name, confidence = normalize_name("123456")

    assert name is None
