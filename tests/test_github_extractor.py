from transformer.extractors.github_extractor import GitHubExtractor
from transformer.models.core import SourceType


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {"X-RateLimit-Remaining": "1"}
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return self.responses[url]


def test_username_extraction():
    extractor = GitHubExtractor(session=FakeSession({}))

    assert extractor._extract_username("https://github.com/octocat") == "octocat"


def test_profile_parsing():
    extractor = GitHubExtractor(session=FakeSession({}))

    profile = extractor._parse_profile(
        {
            "id": 7,
            "name": "Jashan Singh",
            "html_url": "https://github.com/jashan",
            "bio": "Data engineer",
            "location": "Bangalore",
            "email": "jashan@gmail.com",
            "blog": "jashan.dev",
            "company": "@Acme",
            "followers": 10,
            "following": 5,
        }
    )

    assert profile.source == SourceType.GITHUB
    assert profile.full_name == "Jashan Singh"
    assert profile.emails == ["jashan@gmail.com"]
    assert profile.github_url == "https://github.com/jashan"
    assert profile.portfolio_urls == ["https://jashan.dev"]
    assert profile.extra["company"] == "Acme"


def test_languages_aggregation():
    extractor = GitHubExtractor(session=FakeSession({}))

    languages, topics = extractor._aggregate_repos(
        [
            {"language": "Python", "topics": ["ml"], "stargazers_count": 3},
            {"language": "Go", "topics": ["api"], "stargazers_count": 2},
        ]
    )

    assert languages == {"Python", "Go"}
    assert topics == {"ml", "api"}


def test_topics_aggregation_ignores_forks():
    extractor = GitHubExtractor(session=FakeSession({}))

    languages, topics = extractor._aggregate_repos(
        [
            {"fork": True, "language": "Rust", "topics": ["ignored"]},
            {"language": "Python", "topics": ["docker", "fastapi"]},
        ]
    )

    assert languages == {"Python"}
    assert topics == {"docker", "fastapi"}


from unittest.mock import Mock


def test_extract_username_from_url():
    assert (
        GitHubExtractor._extract_username("https://github.com/Jashan1001")
        == "Jashan1001"
    )


def test_extract_username():
    assert GitHubExtractor._extract_username("octocat") == "octocat"


def test_invalid_username():
    assert GitHubExtractor._extract_username("") is None
    assert GitHubExtractor._extract_username("abc def") is None


def test_parse_profile():
    extractor = GitHubExtractor()

    profile = {
        "id": 1,
        "name": "Jashan Singh",
        "html_url": "https://github.com/Jashan1001",
        "bio": "Software Engineer",
        "location": "Bangalore",
        "company": "@OpenAI",
        "followers": 10,
        "following": 5,
    }

    candidate = extractor._parse_profile(profile)

    assert candidate.full_name == "Jashan Singh"
    assert candidate.github_url.endswith("Jashan1001")
    assert candidate.location_raw == "Bangalore"
    assert candidate.extra["company"] == "OpenAI"


def test_language_aggregation():
    extractor = GitHubExtractor()

    repos = [
        {
            "fork": False,
            "language": "Python",
            "topics": [],
            "stargazers_count": 5,
        },
        {
            "fork": False,
            "language": "Dockerfile",
            "topics": [],
            "stargazers_count": 2,
        },
    ]

    languages, topics = extractor._aggregate_repos(repos)

    assert languages == {
        "Python",
        "Dockerfile",
    }

    assert topics == set()


def test_topic_aggregation():
    extractor = GitHubExtractor()

    repos = [
        {
            "fork": False,
            "language": "Python",
            "topics": [
                "redis",
                "docker",
            ],
            "stargazers_count": 5,
        }
    ]

    languages, topics = extractor._aggregate_repos(repos)

    assert "redis" in topics
    assert "docker" in topics


def test_ignore_forks():
    extractor = GitHubExtractor()

    repos = [
        {
            "fork": True,
            "language": "Python",
            "topics": ["redis"],
            "stargazers_count": 100,
        }
    ]

    languages, topics = extractor._aggregate_repos(repos)

    assert languages == set()
    assert topics == set()


def test_top_repositories():
    extractor = GitHubExtractor()

    repos = [
        {
            "fork": False,
            "name": "repo1",
            "stargazers_count": 20,
            "forks_count": 5,
        },
        {
            "fork": False,
            "name": "repo2",
            "stargazers_count": 10,
            "forks_count": 1,
        },
    ]

    top = extractor._top_repo_names(repos)

    assert top == [
        "repo1",
        "repo2",
    ]


def test_extract_with_mocked_api():
    session = Mock()

    profile_response = Mock()
    profile_response.ok = True
    profile_response.status_code = 200
    profile_response.headers = {"X-RateLimit-Remaining": "10"}
    profile_response.json.return_value = {
        "id": 1,
        "name": "Jashan Singh",
        "html_url": "https://github.com/Jashan1001",
    }

    repo_response = Mock()
    repo_response.ok = True
    repo_response.status_code = 200
    repo_response.headers = {"X-RateLimit-Remaining": "10"}
    repo_response.json.return_value = []

    session.get.side_effect = [
        profile_response,
        repo_response,
    ]

    extractor = GitHubExtractor(session=session)

    candidate = extractor.extract("Jashan1001")

    assert candidate.full_name == "Jashan Singh"


def test_rate_limit_degrades_immediately_without_blocking():
    """
    Regression test: _get() used to call time.sleep() (capped at 60s)
    when the rate limit was hit, then check resp.status_code on the
    SAME already-fetched response -- it never retried. That meant a
    rate-limited call would block the whole pipeline for up to a
    minute and still fail afterward, for zero benefit. This test fails
    if a sleep is ever reintroduced on this path, by asserting the
    call completes well under a second.
    """
    import time as time_module

    rate_limited_response = Mock()
    rate_limited_response.ok = False
    rate_limited_response.status_code = 403
    rate_limited_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time_module.time()) + 1800),
    }

    session = Mock()
    session.get.return_value = rate_limited_response

    extractor = GitHubExtractor(session=session)

    started = time_module.monotonic()
    candidate = extractor.extract("someone-rate-limited")
    elapsed = time_module.monotonic() - started

    assert elapsed < 1.0, "rate-limit handling must not block the pipeline"
    assert candidate.full_name is None  # degraded gracefully, no crash