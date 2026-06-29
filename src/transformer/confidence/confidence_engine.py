"""
Confidence scoring engine.

This module assigns confidence scores to the merged CanonicalProfile.

Confidence is based on four independent signals:

1. Source reliability
2. Extraction / normalization confidence
3. Agreement between multiple sources
4. Candidate profile completeness

The engine never changes candidate data.
It only updates confidence values.
"""

from __future__ import annotations

from statistics import mean

from transformer.models.core import (
    CanonicalProfile,
    Provenance,
    SOURCE_BASE_CONFIDENCE,
)


class ConfidenceEngine:
    """
    Computes confidence scores for a CanonicalProfile.
    """

    # ---------------------------------------------
    # Public API
    # ---------------------------------------------

    def compute(self, profile: CanonicalProfile) -> CanonicalProfile:
        """
        Computes overall confidence and returns the same profile.
        """

        field_scores = self._field_scores(profile.provenance)

        completeness = self._profile_completeness(profile)

        overall = self._overall_score(field_scores, completeness)

        profile.overall_confidence = max(0.0, min(1.0, round(overall, 3)))

        return profile

    # ---------------------------------------------
    # Field scoring
    # ---------------------------------------------

    def _field_scores(
        self,
        provenance: list[Provenance],
    ) -> dict[str, float]:

        grouped: dict[str, list[Provenance]] = {}

        for p in provenance:
            grouped.setdefault(p.field, []).append(p)

        scores = {}

        for field, records in grouped.items():
            scores[field] = self._score_field(records)

        return scores

    def _score_field(
        self,
        records: list[Provenance],
    ) -> float:

        if not records:
            return 0.0

        source_scores = []

        for r in records:
            base = SOURCE_BASE_CONFIDENCE.get(r.source, 0.5)

            source_scores.append((base + r.confidence) / 2)

        score = mean(source_scores)

        score += self._agreement_bonus(records)

        return min(score, 1.0)

    # ---------------------------------------------
    # Agreement
    # ---------------------------------------------

    def _agreement_bonus(
        self,
        records: list[Provenance],
    ) -> float:

        if len(records) <= 1:
            return 0.0

        unique_sources = {r.source for r in records}

        if len(unique_sources) >= 3:
            return 0.10

        if len(unique_sources) == 2:
            return 0.05

        return 0.0

    # ---------------------------------------------
    # Completeness
    # ---------------------------------------------

    def _profile_completeness(
        self,
        profile: CanonicalProfile,
    ) -> float:

        fields = [
            profile.full_name,
            profile.emails,
            profile.phones,
            profile.location,
            profile.headline,
            profile.skills,
            profile.experience,
            profile.education,
        ]

        present = 0

        for value in fields:
            if value is None:
                continue

            if isinstance(value, list) and not value:
                continue

            present += 1

        return present / len(fields)

    # ---------------------------------------------
    # Final score
    # ---------------------------------------------

    def _overall_score(
        self,
        field_scores: dict[str, float],
        completeness: float,
    ) -> float:

        if field_scores:
            confidence = mean(field_scores.values())
        else:
            confidence = 0.0

        # Give profile completeness a modest influence.
        return confidence * 0.9 + completeness * 0.1
