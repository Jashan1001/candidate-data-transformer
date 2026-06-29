"""
Merge Engine — produces one CanonicalProfile from N RawCandidates.

Pipeline:
  1. Normalize every RawCandidate (phones, emails, dates, skills, …)
  2. Build FieldObservations — one per (field, source)
  3. Apply resolution policy per field type:
     • Scalar   → source-priority winner; ties broken by confidence
     • List     → union, deduplicated, sorted by confidence
     • Complex  → structured merge (skills, experience, education)
  4. Populate provenance records for every resolved field
  5. Return a CanonicalProfile with _observations attached for debugging
"""

from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
import uuid
from typing import Any

from transformer.models.core import (
    CanonicalProfile,
    EducationCanonical,
    ExperienceCanonical,
    FieldObservation,
    LinksCanonical,
    LocationCanonical,
    Provenance,
    RawCandidate,
    SkillCanonical,
    SOURCE_BASE_CONFIDENCE,
    SOURCE_PRIORITY,
    SourceType,
)
from transformer.normalizers import (
    canonicalize_skills,
    normalize_date,
    normalize_emails,
    normalize_location,
    normalize_name,
    normalize_phones,
)
from transformer.utils.helpers import deduplicate, generate_candidate_id, safe_float
from transformer.utils.logger import get_logger

log = get_logger(__name__)

# How much the confidence drops each time a value conflicts across sources
_CONFLICT_PENALTY = 0.05

# Minimum confidence threshold — below this the field is treated as absent
_MIN_CONFIDENCE = 0.1

_SOURCE_PRIORITY_INDEX = {src: i for i, src in enumerate(SOURCE_PRIORITY)}
_LOWEST_PRIORITY = 999


class MergeEngine:
    """
    Stateless merge engine.  Call ``merge()`` to produce a CanonicalProfile.
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def merge(
        self,
        raws: list[RawCandidate],
        *,
        candidate_id: str | None = None,
    ) -> CanonicalProfile:
        """
        Merge a list of RawCandidates (one per source) into a single
        CanonicalProfile.

        Parameters
        ----------
        raws : list[RawCandidate]
            Output of the extraction layer; may be empty or contain a single item.
        candidate_id : str | None
            If provided, overrides auto-generated ID.

        Returns
        -------
        CanonicalProfile
            Fully merged, normalised, de-duplicated profile.
        """
        if not raws:
            log.warning("MergeEngine received empty source list")
            return CanonicalProfile(candidate_id=generate_candidate_id())

        log.info("Merging sources", count=len(raws), sources=[r.source for r in raws])

        # Step 1 — normalise each raw record in-place (we work on copies)
        normalised = [self._normalise_raw(r) for r in raws]

        # Step 2 — collect all field observations
        obs: dict[str, list[FieldObservation]] = defaultdict(list)
        for raw in normalised:
            self._collect_observations(raw, obs)

        # Step 3 — resolve each field
        profile = CanonicalProfile(
            candidate_id=candidate_id or self._resolve_id(normalised),
        )
        profile._observations = dict(obs)

        provenance: list[Provenance] = []

        profile.full_name = self._resolve_scalar("full_name", obs, provenance)
        profile.headline = self._resolve_scalar("headline", obs, provenance)
        profile.years_experience = safe_float(
            self._resolve_scalar("years_experience", obs, provenance)
        )
        profile.location = self._resolve_location(obs, provenance)
        profile.emails = self._resolve_list("emails", obs, provenance)
        profile.phones = self._resolve_list("phones", obs, provenance)
        profile.links = self._resolve_links(obs, provenance)
        profile.skills = self._resolve_skills(obs, provenance)
        profile.experience = self._resolve_experience(normalised)
        profile.education = self._resolve_education(normalised)

        profile.provenance = provenance

        log.info(
            "Merge complete",
            candidate_id=profile.candidate_id,
            emails=len(profile.emails),
            phones=len(profile.phones),
            skills=len(profile.skills),
        )
        return profile

    # ------------------------------------------------------------------
    # Step 1 — normalisation of a single raw record
    # ------------------------------------------------------------------

    def _normalise_raw(self, raw: RawCandidate) -> RawCandidate:
        """
        Return a copy of *raw* with normalised field values applied.
        We mutate the copy's lists and scalars so observations later
        carry already-normalised values.
        """
        r = deepcopy(raw)

        # Name
        if r.full_name:
            norm, _ = normalize_name(r.full_name)
            r.full_name = norm

        # Emails
        r.emails = [e for e, _ in normalize_emails(r.emails)]

        # Phones
        r.phones = [p for p, _ in normalize_phones(r.phones)]

        # Skills — canonicalise in place
        r.skills_raw = [name for name, _ in canonicalize_skills(r.skills_raw)]

        return r

    # ------------------------------------------------------------------
    # Step 2 — observation collection
    # ------------------------------------------------------------------

    def _collect_observations(
        self,
        raw: RawCandidate,
        obs: dict[str, list[FieldObservation]],
    ) -> None:
        src = raw.source
        base = SOURCE_BASE_CONFIDENCE[src]

        def _add(
            field: str, value: Any, conf: float = base, method: str = "extracted"
        ) -> None:
            if value is None or (isinstance(value, (str, list)) and not value):
                return
            obs[field].append(
                FieldObservation(
                    field=field,
                    value=value,
                    source=src,
                    confidence=min(conf, 1.0),
                    method=method,
                )
            )

        _add("full_name", raw.full_name)
        _add("headline", raw.headline)
        _add("years_experience", raw.years_experience)
        _add("location_raw", raw.location_raw)
        _add("linkedin_url", raw.linkedin_url)
        _add("github_url", raw.github_url)

        if raw.emails:
            _add("emails", raw.emails, conf=base, method="normalized")
        if raw.phones:
            _add("phones", raw.phones, conf=base, method="normalized")
        if raw.skills_raw:
            _add("skills", raw.skills_raw, conf=base, method="normalized")
        if raw.portfolio_urls:
            _add("portfolio_urls", raw.portfolio_urls)

    # ------------------------------------------------------------------
    # Step 3a — scalar resolution (source-priority + confidence)
    # ------------------------------------------------------------------

    def _resolve_scalar(
        self,
        field: str,
        obs: dict[str, list[FieldObservation]],
        provenance: list[Provenance],
        *,
        allow_none: bool = True,
    ) -> Any:
        candidates = obs.get(field, [])
        if not candidates:
            return None

        # Sort by source priority (lower index = higher priority)
        def _priority(o: FieldObservation) -> tuple[int, float]:
            prio = _SOURCE_PRIORITY_INDEX.get(o.source, _LOWEST_PRIORITY)
            return prio, -o.confidence  # negate confidence so higher sorts first

        sorted_obs = sorted(candidates, key=_priority)
        winner = sorted_obs[0]

        # Apply a small confidence penalty for each conflicting value
        unique_values = {self._scalar_fingerprint(o.value) for o in candidates}
        unique_values.discard(None)
        n_conflicts = max(len(unique_values) - 1, 0)
        final_conf = max(
            winner.confidence - n_conflicts * _CONFLICT_PENALTY, _MIN_CONFIDENCE
        )

        if winner.value is None and not allow_none:
            return None

        observed_sources = sorted({o.source.value for o in candidates})

        provenance.append(
            Provenance(
                field=field,
                source=winner.source,
                method=winner.method,
                confidence=round(final_conf, 4),
                raw_value=winner.value,
                observed_sources=observed_sources,
            )
        )

        log.debug(
            "Resolved scalar",
            field=field,
            winner_source=winner.source,
            confidence=round(final_conf, 4),
            conflicts=n_conflicts,
        )
        return winner.value

    # ------------------------------------------------------------------
    # Step 3b — list resolution (union + dedup)
    # ------------------------------------------------------------------

    def _resolve_list(
        self,
        field: str,
        obs: dict[str, list[FieldObservation]],
        provenance: list[Provenance],
    ) -> list[str]:
        """
        Union all observed lists; deduplicate; sort by source priority so
        highest-priority sources appear first.
        """
        candidates = obs.get(field, [])
        if not candidates:
            return []

        seen: set[str] = set()
        result: list[str] = []

        # Iterate in source-priority order
        ordered = sorted(
            candidates,
            key=lambda o: _SOURCE_PRIORITY_INDEX.get(o.source, _LOWEST_PRIORITY),
        )
        best_conf = 0.0
        best_source: SourceType = ordered[0].source

        for obs_item in ordered:
            vals = (
                obs_item.value if isinstance(obs_item.value, list) else [obs_item.value]
            )
            for val in vals:
                norm = str(val).strip()
                if norm and norm not in seen:
                    seen.add(norm)
                    result.append(norm)
                    if obs_item.confidence > best_conf:
                        best_conf = obs_item.confidence
                        best_source = obs_item.source

        if result:
            provenance.append(
                Provenance(
                    field=field,
                    source=best_source,
                    method="union",
                    confidence=round(best_conf, 4),
                    raw_value=deduplicate(result),
                    observed_sources=sorted({o.source.value for o in candidates}),
                )
            )

        return deduplicate(result)

    # ------------------------------------------------------------------
    # Step 3c — location resolution
    # ------------------------------------------------------------------

    def _resolve_location(
        self,
        obs: dict[str, list[FieldObservation]],
        provenance: list[Provenance],
    ) -> LocationCanonical | None:
        candidates = obs.get("location_raw", [])
        if not candidates:
            return None

        best: tuple[LocationCanonical | None, float, SourceType | None, Any] = (
            None,
            0.0,
            None,
            None,
        )
        for o in sorted(
            candidates,
            key=lambda o: _SOURCE_PRIORITY_INDEX.get(o.source, _LOWEST_PRIORITY),
        ):
            loc, conf = normalize_location(str(o.value))
            effective_conf = conf * o.confidence
            if loc and effective_conf > best[1]:
                best = (loc, effective_conf, o.source, o.value)

        resolved, conf, src, raw_value = best
        if resolved and src:
            provenance.append(
                Provenance(
                    field="location",
                    source=src,
                    method="normalized",
                    confidence=round(conf, 4),
                    raw_value=raw_value,
                    observed_sources=sorted({o.source.value for o in candidates}),
                )
            )
        return resolved

    # ------------------------------------------------------------------
    # Step 3d — links resolution
    # ------------------------------------------------------------------

    def _resolve_links(
        self,
        obs: dict[str, list[FieldObservation]],
        provenance: list[Provenance],
    ) -> LinksCanonical:
        linkedin = self._resolve_scalar("linkedin_url", obs, provenance)
        github = self._resolve_scalar("github_url", obs, provenance)
        portfolio = self._resolve_list("portfolio_urls", obs, provenance)
        return LinksCanonical(
            linkedin=linkedin,
            github=github,
            portfolio=[
                u for u in portfolio if "linkedin" not in u and "github" not in u
            ],
            other=[],
        )

    # ------------------------------------------------------------------
    # Step 3e — skills resolution (multi-source union with confidence)
    # ------------------------------------------------------------------

    def _resolve_skills(
        self,
        obs: dict[str, list[FieldObservation]],
        provenance: list[Provenance],
    ) -> list[SkillCanonical]:
        candidates = obs.get("skills", [])
        if not candidates:
            return []

        # skill_name → {source_name: confidence}
        skill_map: dict[str, dict[str, float]] = defaultdict(dict)

        for o in candidates:
            raw_skills = o.value if isinstance(o.value, list) else [o.value]
            for skill_name in raw_skills:
                if skill_name:
                    # already canonicalized in _normalise_raw
                    skill_map[skill_name][o.source.value] = o.confidence

        result: list[SkillCanonical] = []
        for name, src_conf in skill_map.items():
            sources = list(src_conf.keys())
            # Confidence boosted when skill appears in multiple sources
            base_conf = max(src_conf.values())
            multi_source_bonus = min(0.05 * (len(sources) - 1), 0.15)
            final_conf = min(base_conf + multi_source_bonus, 1.0)
            result.append(
                SkillCanonical(
                    name=name,
                    confidence=round(final_conf, 4),
                    sources=sources,
                )
            )

        result.sort(key=lambda s: (-s.confidence, s.name))

        if result:
            source_confidence: dict[SourceType, float] = defaultdict(float)
            for o in candidates:
                source_confidence[o.source] = max(
                    source_confidence[o.source], o.confidence
                )

            best_source = max(
                source_confidence.items(),
                key=lambda kv: (
                    kv[1],
                    -_SOURCE_PRIORITY_INDEX.get(kv[0], _LOWEST_PRIORITY),
                ),
            )[0]
            provenance.append(
                Provenance(
                    field="skills",
                    source=best_source,
                    method="union",
                    confidence=round(
                        sum(s.confidence for s in result) / len(result), 4
                    ),
                    raw_value=f"{len(result)} skills merged",
                    observed_sources=sorted({o.source.value for o in candidates}),
                )
            )

        return result

    # ------------------------------------------------------------------
    # Step 3f — experience merge (best-effort dedup by company+title)
    # ------------------------------------------------------------------

    def _resolve_experience(
        self,
        raws: list[RawCandidate],
    ) -> list[ExperienceCanonical]:
        seen: set[str] = set()
        result: list[ExperienceCanonical] = []

        # Priority: resume sources first (most detail), then ATS
        ordered = sorted(
            raws,
            key=lambda r: _SOURCE_PRIORITY_INDEX.get(r.source, _LOWEST_PRIORITY),
        )

        for raw in ordered:
            for entry in raw.experience_raw:
                title = str(entry.get("title") or "").strip()
                company = str(entry.get("company") or "").strip()
                key = f"{title.lower()}|{company.lower()}"
                if key in seen:
                    continue
                seen.add(key)

                start_raw = str(entry.get("start") or "")
                end_raw = str(entry.get("end") or "")
                start, _ = normalize_date(start_raw)
                end, _ = normalize_date(end_raw)

                result.append(
                    ExperienceCanonical(
                        company=company or None,
                        title=title or None,
                        start=start,
                        end=end,
                        summary=str(entry.get("summary") or "").strip() or None,
                    )
                )

        return result

    # ------------------------------------------------------------------
    # Step 3g — education merge (dedup by institution+degree)
    # ------------------------------------------------------------------

    def _resolve_education(
        self,
        raws: list[RawCandidate],
    ) -> list[EducationCanonical]:
        seen: set[str] = set()
        result: list[EducationCanonical] = []

        for raw in raws:
            for entry in raw.education_raw:
                institution = str(entry.get("institution") or "").strip()
                degree = str(entry.get("degree") or "").strip()
                key = f"{institution.lower()}|{degree.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                result.append(
                    EducationCanonical(
                        institution=institution or None,
                        degree=degree or None,
                        field=entry.get("field"),
                        end_year=entry.get("end_year"),
                    )
                )

        return result

    # ------------------------------------------------------------------
    # Candidate ID resolution
    # ------------------------------------------------------------------

    def _resolve_id(self, raws: list[RawCandidate]) -> str:
        # Prefer ATS raw_id, then first email, then first phone, then name
        for r in sorted(
            raws,
            key=lambda r: _SOURCE_PRIORITY_INDEX.get(r.source, _LOWEST_PRIORITY),
        ):
            if r.raw_id:
                return r.raw_id
        all_emails = [e for r in raws for e in r.emails]
        all_phones = [p for r in raws for p in r.phones]
        all_names = [r.full_name for r in raws if r.full_name]
        if all_emails:
            return generate_candidate_id(email=all_emails[0])
        if all_phones:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, all_phones[0].strip().lower()))
        return generate_candidate_id(name=all_names[0] if all_names else None)

    @staticmethod
    def _scalar_fingerprint(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool):
            return ("bool", value)
        if isinstance(value, (int, float)):
            return ("num", float(value))
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            number = safe_float(stripped)
            if number is not None:
                return ("num", number)
            return ("str", stripped.lower())
        return ("other", str(value).strip().lower())