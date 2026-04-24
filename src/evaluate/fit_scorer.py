"""FitScorer — builds the profile input and delegates to FitScoringAgent."""

from __future__ import annotations

from core.config import ScoringWeights
from evaluate.agent import FitResult, FitScoringAgent


class FitScorer:
    def __init__(self, weights: ScoringWeights | None = None, model: str | None = None) -> None:
        self._weights = weights or ScoringWeights()
        self._model = model

    def compute_final_score(self, result: FitResult) -> float:
        w = self._weights
        raw = (
            result.score * w.fit
            + result.location_score * w.location
            + result.seniority_score * w.seniority
            + result.compensation_score * w.compensation
        )
        return round(min(10.0, max(0.1, raw)), 1)

    def build_profile_input(self, profile: dict) -> dict:
        return {
            "headline": profile.get("narrative", {}).get("headline"),
            "primary_roles": profile.get("targets", {}).get("primary_roles", []),
            "skill_tiers": profile.get("skill_tiers", {}),
            "mission_domains": profile.get("mission_domains", {}),
            "location_preferences": profile.get("location_preferences", {}),
            "compensation": profile.get("compensation", {}),
        }

    async def score(self, job: dict, profile_input: dict) -> tuple[FitResult, list[str]] | None:
        result = await FitScoringAgent(model=self._model).score(job, profile_input)
        if result is None:
            return None
        all_skills = {
            s.lower()
            for tier in profile_input.get("skill_tiers", {}).values()
            for s in tier
        }
        matched_skills = [
            s for s in job.get("tech_stack", [])
            if s.lower() in all_skills
        ]
        return result, matched_skills
