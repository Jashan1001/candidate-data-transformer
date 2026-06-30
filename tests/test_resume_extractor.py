from transformer.extractors.resume_extractor import ResumeExtractor


def test_empty_resume():
    extractor = ResumeExtractor()

    candidate = extractor.extract("")

    assert candidate.full_name is None
    assert candidate.emails == []
    assert candidate.phones == []


def test_extract_email():
    text = """
    Jashan Singh

    Email:
    jashan@gmail.com
    """

    candidate = ResumeExtractor().extract(text)

    assert candidate.emails == ["jashan@gmail.com"]


def test_extract_phone():
    text = """
    Phone:
    +91 9876543210
    """

    candidate = ResumeExtractor().extract(text)

    assert len(candidate.phones) == 1


def test_extract_name():
    text = """
    Jashan Singh

    Software Engineer
    """

    candidate = ResumeExtractor().extract(text)

    assert candidate.full_name == "Jashan Singh"


def test_extract_skills():
    text = """
    Skills

    Python
    Docker
    Redis
    Kafka
    """

    candidate = ResumeExtractor().extract(text)

    assert "Python" in candidate.skills_raw
    assert "Docker" in candidate.skills_raw


def test_extract_experience():
    text = """
    Experience

    Software Engineer

    3 years
    """

    candidate = ResumeExtractor().extract(text)

    assert candidate.years_experience == 3


def test_extract_linkedin():
    text = """
    https://linkedin.com/in/jashan
    """

    candidate = ResumeExtractor().extract(text)

    assert candidate.linkedin_url.endswith("/jashan")


def test_extract_github():
    text = """
    https://github.com/Jashan1001
    """

    candidate = ResumeExtractor().extract(text)

    assert candidate.github_url.endswith("Jashan1001")


def test_invalid_resume():
    candidate = ResumeExtractor().extract("%%%%%%%")

    assert candidate is not None


def test_three_part_location_is_not_truncated():
    """
    Regression test: a "City, Region, Country" location used to get
    truncated to "City, Xx" because the 2-letter US-state-code regex
    alternative matched first and grabbed just the first two letters
    of the region name (e.g. "Ka" out of "Karnataka").
    """
    text = """
    Priya Mehraa
    Bengaluru, Karnataka, India
    priya.mehra@gmail.com
    """

    candidate = ResumeExtractor().extract(text)

    assert candidate.location_raw == "Bengaluru, Karnataka, India"