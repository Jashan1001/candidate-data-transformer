"""
GitHub profile extractor — production quality.

Fetches:
  - User profile  (name, bio, company, location, blog, email)
  - Top repositories (primary languages → skill inference)
  - Repository topics (explicit technology tags)

Rate-limit aware:
  - Uses GITHUB_TOKEN env-var when present (5 000 req/h vs 60 req/h)
  - Reads X-RateLimit-Remaining and backs off gracefully
  - Returns an empty RawCandidate on any API error rather than crashing
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

import requests

from transformer.extractors import BaseExtractor
from transformer.models.core import RawCandidate, SourceType
from transformer.utils.logger import get_logger

log = get_logger(__name__)

_API_BASE = "https://api.github.com"
_MAX_REPOS = 100  # fetch at most this many repos
_TIMEOUT = 15  # seconds per request


class GitHubExtractor(BaseExtractor):
    """
    Extracts a RawCandidate from a GitHub username or profile URL.

    Parameters
    ----------
    session : requests.Session | None
        Optional pre-configured session (useful for testing / mocking).
    """

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or self._build_session()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract(self, username_or_url: str) -> RawCandidate:  # type: ignore[override]
        username = self._extract_username(username_or_url)
        if not username:
            log.warning("Could not resolve GitHub username", input=username_or_url)
            return self._empty()

        log.info("Fetching GitHub profile", username=username)

        profile = self._get(f"/users/{username}")
        if profile is None:
            return self._empty()

        rc = self._parse_profile(profile)

        # Enrich with repository languages + topics
        repos = self._get(
            f"/users/{username}/repos",
            params={
                "per_page": _MAX_REPOS,
                "sort": "pushed",
                "type": "owner",
            },
        )
        if repos:
            languages, topics = self._aggregate_repos(repos)
            rc.skills_raw = sorted(languages | topics)
            rc.extra["public_repos"] = profile.get("public_repos", 0)
            rc.extra["top_repos"] = self._top_repo_names(repos, n=5)

        log.info(
            "GitHub extraction complete",
            username=username,
            skills=len(rc.skills_raw),
        )
        return rc

    # ------------------------------------------------------------------
    # Profile → RawCandidate
    # ------------------------------------------------------------------

    def _parse_profile(self, data: dict[str, Any]) -> RawCandidate:
        rc = RawCandidate(source=SourceType.GITHUB)

        rc.raw_id = str(data.get("id", "")) or None
        rc.full_name = data.get("name") or None
        rc.github_url = data.get("html_url") or None
        rc.headline = data.get("bio") or None
        rc.location_raw = data.get("location") or None

        # GitHub may expose a public email
        if data.get("email"):
            rc.emails = [data["email"]]

        # Blog / website
        blog = data.get("blog") or ""
        if blog and blog.strip():
            blog = blog.strip()
            if not blog.startswith("http"):
                blog = "https://" + blog
            if "linkedin.com" in blog:
                rc.linkedin_url = blog
            else:
                if blog not in rc.portfolio_urls:
                    rc.portfolio_urls.append(blog)

        # Employer
        company = (data.get("company") or "").strip().lstrip("@")
        if company:
            rc.extra["company"] = company

        rc.extra["followers"] = data.get("followers", 0)
        rc.extra["following"] = data.get("following", 0)

        return rc

    # ------------------------------------------------------------------
    # Repo aggregation
    # ------------------------------------------------------------------

    def _aggregate_repos(
        self,
        repos: Iterable[dict[str, Any]],
    ) -> tuple[set[str], set[str]]:
        """
        Return (languages, topics) as sets of strings.

        Languages are weighted by stargazer_count of the repo they appear in,
        so popular repos contribute more signal. We keep the top-N.
        """
        lang_weight: dict[str, int] = {}
        topics: set[str] = set()

        for repo in repos:
            if repo.get("fork"):  # ignore forked repos
                continue
            lang = repo.get("language")
            if lang:
                stars = repo.get("stargazers_count", 0)
                lang_weight[lang] = lang_weight.get(lang, 0) + max(stars, 1)
            for topic in repo.get("topics", []):
                if topic:
                    topics.add(topic)

        # Keep languages seen across repos (not just highest weight)
        languages = set(lang_weight.keys())
        return languages, topics

    def _top_repo_names(self, repos: Iterable[dict[str, Any]], n: int = 5) -> list[str]:
        repos = list(repos)
        non_forks = [r for r in repos if not r.get("fork")]
        sorted_repos = sorted(
            non_forks,
            key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0)),
            reverse=True,
        )
        return [r["name"] for r in sorted_repos[:n] if r.get("name")]

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        url = _API_BASE + path
        try:
            resp = self._session.get(url, params=params, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            log.warning("GitHub HTTP error", url=url, error=str(exc))
            return None

        # Rate-limit handling
        remaining = int(resp.headers.get("X-RateLimit-Remaining", 1))
        if remaining == 0:
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
            wait = max(reset_ts - int(time.time()), 0) + 1
            log.warning("GitHub rate limit hit — waiting", seconds=wait)
            time.sleep(min(wait, 60))  # cap at 60 s in pipelines

        if resp.status_code == 404:
            log.warning("GitHub resource not found", path=path)
            return None
        if resp.status_code == 403:
            log.error("GitHub access denied (rate limit or private)", path=path)
            return None
        if not resp.ok:
            log.warning("GitHub non-200 response", status=resp.status_code, path=path)
            return None

        try:
            return resp.json()
        except ValueError:
            return None

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            log.debug("GITHUB_TOKEN found — using authenticated session")
        session.headers.update(headers)
        return session

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_username(value: str) -> str | None:
        if not value or not value.strip():
            return None
        value = value.strip()
        if "github.com" in value:
            parsed = urlparse(value if "://" in value else "https://" + value)
            parts = [p for p in parsed.path.split("/") if p]
            return parts[0] if parts else None
        # Reject obvious non-usernames
        if " " in value or "@" in value:
            return None
        return value

    def _empty(self) -> RawCandidate:
        return RawCandidate(source=SourceType.GITHUB)
