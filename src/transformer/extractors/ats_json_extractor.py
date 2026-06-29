"""
ATS JSON blob extractor.

ATS systems use their own schema — field names do NOT match ours.
We handle two realistic ATS flavors:
  - Greenhouse-style: candidate.name, candidate.email_addresses[], etc.
  - Lever-style: name, emails[], phones[], applications[].job.title, etc.

Unknown structure → best-effort key-sniffing.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from transformer.extractors import BaseExtractor
from transformer.models.core import RawCandidate, SourceType


class ATSJsonExtractor(BaseExtractor):

    def extract(
        self,
        source_input: str | Path | dict[str, Any],
    ) -> RawCandidate:
        data = self._load(source_input)
        if not data:
            return self._empty()

        # Detect flavor
        if "candidate" in data and isinstance(data["candidate"], dict):
            return self._parse_greenhouse(data)
        if "applications" in data or "emails" in data:
            return self._parse_lever(data)
        # Generic key-sniffing fallback
        return self._parse_generic(data)

    # ------------------------------------------------------------------
    # Greenhouse flavor
    # ------------------------------------------------------------------
    def _parse_greenhouse(self, data: dict) -> RawCandidate:
        c = data.get("candidate", {})
        rc = RawCandidate(source=SourceType.ATS_JSON)
        rc.raw_id = str(data.get("id", c.get("id", ""))) or None
        rc.full_name = c.get("name") or f"{c.get('first_name','')} {c.get('last_name','')}".strip() or None
        rc.emails = [e["value"] for e in c.get("email_addresses", []) if e.get("value")]
        rc.phones = [p["value"] for p in c.get("phone_numbers", []) if p.get("value")]
        address = c.get("addresses", [{}])[0] if c.get("addresses") else {}
        rc.location_raw = address.get("value") or c.get("location", {}).get("name")
        rc.linkedin_url = self._find_url(c.get("website_addresses", []), "linkedin")
        rc.github_url = self._find_url(c.get("website_addresses", []), "github")
        apps = data.get("applications", [])
        if apps:
            rc.headline = apps[0].get("jobs", [{}])[0].get("name") if apps[0].get("jobs") else None
        rc.skills_raw = [t["name"] for t in c.get("tags", []) if t.get("name")]
        return rc

    # ------------------------------------------------------------------
    # Lever flavor
    # ------------------------------------------------------------------
    def _parse_lever(self, data: dict) -> RawCandidate:
        rc = RawCandidate(source=SourceType.ATS_JSON)
        rc.raw_id = str(data.get("id", "")) or None
        rc.full_name = data.get("name")
        emails = data.get("emails", [])
        rc.emails = [
            e.get("value", e.get("email", ""))
            if isinstance(e, dict)
            else str(e)
            for e in emails
        ]
        rc.emails = [e for e in rc.emails if e]
        rc.phones = [p.get("value", p) if isinstance(p, dict) else p for p in data.get("phones", [])]
        location = data.get("location") or data.get("origin") or ""
        rc.location_raw = location if isinstance(location, str) else None
        links = data.get("links", [])
        for link in links:
            url = link if isinstance(link, str) else link.get("url", "")
            if "linkedin" in url:
                rc.linkedin_url = url
            elif "github" in url:
                rc.github_url = url
            else:
                rc.portfolio_urls.append(url)
        app = data.get("applications", [{}])[0] if data.get("applications") else {}
        rc.headline = app.get("posting", {}).get("text") if isinstance(app.get("posting"), dict) else None
        tags = data.get("tags", [])
        rc.skills_raw = [
            t.get("name", "")
            if isinstance(t, dict)
            else str(t)
            for t in tags
        ]
        rc.skills_raw = [s for s in rc.skills_raw if s]
        yoe = data.get("years_experience") or data.get("yearsExperience")
        if yoe is not None and str(yoe).strip():
            try:
                rc.years_experience = float(yoe)
            except (ValueError, TypeError):
                pass
        return rc

    # ------------------------------------------------------------------
    # Generic key-sniffing
    # ------------------------------------------------------------------
    def _parse_generic(self, data: dict) -> RawCandidate:
        rc = RawCandidate(source=SourceType.ATS_JSON)
        rc.raw_id = str(data.get("id", data.get("candidate_id", ""))) or None
        rc.full_name = (
            data.get("full_name") or data.get("name")
            or f"{data.get('first_name','').strip()} {data.get('last_name','').strip()}".strip()
            or None
        )
        # Emails — could be string or list
        email_val = data.get("email") or data.get("email_address") or data.get("emails", [])
        rc.emails = self._coerce_list(email_val)
        # Phones
        phone_val = data.get("phone") or data.get("phone_number") or data.get("phones", [])
        rc.phones = self._coerce_list(phone_val)
        rc.location_raw = data.get("location") or data.get("address") or data.get("city")
        rc.linkedin_url = data.get("linkedin") or data.get("linkedin_url")
        rc.github_url = data.get("github") or data.get("github_url")
        rc.headline = data.get("headline") or data.get("title") or data.get("current_title")
        yoe = data.get("years_experience") or data.get("experience_years") or data.get("yoe")
        if yoe is not None and str(yoe).strip():
            try:
                rc.years_experience = float(yoe)
            except (ValueError, TypeError):
                pass
        skills = data.get("skills", [])
        rc.skills_raw = self._coerce_list(skills)
        return rc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load(self, source_input: str | Path | dict[str, Any]) -> dict[str, Any]:
        if isinstance(source_input, dict):
            return source_input
        if isinstance(source_input, (str, Path)):
            path = Path(source_input)
            if path.exists():
                with open(
                    path,
                    encoding="utf-8",
                    errors="replace",
                ) as f:
                    try:
                        return json.load(f)
                    except json.JSONDecodeError:
                        return {}
            # Might be raw JSON string
            try:
                return json.loads(str(source_input))
            except json.JSONDecodeError:
                pass
        return {}

    def _find_url(
        self,
        url_list: list[dict[str, Any]],
        keyword: str,
    ) -> str | None:
        for item in url_list:
            url = item.get("value", "") if isinstance(item, dict) else str(item)
            if keyword in url.lower():
                return url
        return None

    def _coerce_list(self, val: Any) -> list[str]:
        if isinstance(val, list):
            result = []
            for item in val:
                if isinstance(item, dict):
                    value = item.get("value") or item.get("email") or item.get("phone")
                    if value:
                        result.append(str(value).strip())
                elif item:
                    result.append(str(item).strip())
            return result
        if isinstance(val, str) and val.strip():
            return [val.strip()]
        return []

    def _empty(self) -> RawCandidate:
        return RawCandidate(source=SourceType.ATS_JSON)