"""
GitHub profile extractor.

Uses the public GitHub REST API to enrich candidate profiles with:
- Name
- Bio
- Company
- Location
- Public repositories
- Followers
- Skills inferred from repository languages

Authentication is optional. If GITHUB_TOKEN is present in the environment,
it is used to increase rate limits.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from transformer.extractors import BaseExtractor
from transformer.models.core import RawCandidate, SourceType


class GitHubExtractor(BaseExtractor):
    BASE_URL = "https://api.github.com/users"

    def extract(self, username_or_url: str) -> RawCandidate:
        username = self._extract_username(username_or_url)

        if not username:
            return self._empty()

        headers = {
            "Accept": "application/vnd.github+json"
        }

        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = requests.get(
                f"{self.BASE_URL}/{username}",
                headers=headers,
                timeout=10,
            )

            if response.status_code != 200:
                return self._empty()

            data = response.json()

            rc = RawCandidate(source=SourceType.GITHUB)

            rc.raw_id = str(data.get("id"))
            rc.full_name = data.get("name")
            rc.github_url = data.get("html_url")
            rc.headline = data.get("bio")
            rc.location_raw = data.get("location")

            company = data.get("company")
            if company:
                rc.extra["company"] = company

            repos = self._fetch_languages(username, headers)

            rc.skills_raw = sorted(repos)

            return rc

        except requests.RequestException:
            return self._empty()

    def _fetch_languages(
        self,
        username: str,
        headers: dict[str, str],
    ) -> set[str]:

        try:
            response = requests.get(
                f"{self.BASE_URL}/{username}/repos",
                headers=headers,
                timeout=10,
            )

            if response.status_code != 200:
                return set()

            repos = response.json()

            languages = set()

            for repo in repos:
                language = repo.get("language")
                if language:
                    languages.add(language)

            return languages

        except requests.RequestException:
            return set()

    def _extract_username(self, value: str) -> str | None:

        if not value:
            return None

        value = value.strip()

        if "github.com/" in value:
            return value.rstrip("/").split("/")[-1]

        return value

    def _empty(self) -> RawCandidate:
        return RawCandidate(source=SourceType.GITHUB)