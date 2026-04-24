"""Unified config loader — assembles per-flow config from profile.yaml,
settings.yaml, and configs/companies.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Per-flow config dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ScoutConfig:
    """Runtime config for the scout flow."""

    title_filter: dict = field(default_factory=dict)
    tracked_companies: list[dict] = field(default_factory=list)
    worker_count: int = 10
    max_pages: int = 10
    respect_robots: bool = True
    model: str | None = None


@dataclass
class EnrichConfig:
    """Runtime config for the enrich flow."""

    concurrency: int = 5
    checkpoint_every: int = 5
    limit: int | None = None
    model: str | None = None


@dataclass
class ScoringWeights:
    fit: float = 0.5
    location: float = 0.2
    seniority: float = 0.2
    compensation: float = 0.1


@dataclass
class EvaluateConfig:
    """Runtime config for the evaluate flow."""

    auto_reject_threshold: float = 4.0
    auto_match_threshold: float = 8.5
    location_reject_threshold: float = 2.0
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    model: str | None = None


# ---------------------------------------------------------------------------
# App-level settings dataclasses (backed by configs/settings.yaml)
# ---------------------------------------------------------------------------

@dataclass
class ScoutSettings:
    respect_robots: bool = True
    max_pages: int = 10
    worker_count: int = 10
    model: str | None = None


@dataclass
class EnrichSettings:
    concurrency: int = 5
    checkpoint_every: int = 5
    model: str | None = None


@dataclass
class EvaluateSettings:
    auto_reject_threshold: float = 4.0
    auto_match_threshold: float = 8.5
    location_reject_threshold: float = 2.0
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    model: str | None = None


@dataclass
class AppSettings:
    scout: ScoutSettings = field(default_factory=ScoutSettings)
    enrich: EnrichSettings = field(default_factory=EnrichSettings)
    evaluate: EvaluateSettings = field(default_factory=EvaluateSettings)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class AppConfigLoader:
    """Loads and assembles all per-flow configs from the project root."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    def settings(self) -> AppSettings:
        raw = self._yaml("configs/settings.yaml")
        s = raw.get("scout", {})
        e = raw.get("enrich", {})
        v = raw.get("evaluate", {})
        w = v.get("scoring_weights", {})
        return AppSettings(
            scout=ScoutSettings(
                respect_robots=s.get("respect_robots", True),
                max_pages=s.get("max_pages", 10),
                worker_count=s.get("worker_count", 10),
                model=s.get("model") or None,
            ),
            enrich=EnrichSettings(
                concurrency=e.get("concurrency", 5),
                checkpoint_every=e.get("checkpoint_every", 5),
                model=e.get("model") or None,
            ),
            evaluate=EvaluateSettings(
                auto_reject_threshold=v.get("auto_reject_threshold", 4.0),
                auto_match_threshold=v.get("auto_match_threshold", 8.5),
                location_reject_threshold=v.get("location_reject_threshold", 2.0),
                scoring_weights=ScoringWeights(
                    fit=w.get("fit", 0.5),
                    location=w.get("location", 0.2),
                    seniority=w.get("seniority", 0.2),
                    compensation=w.get("compensation", 0.1),
                ),
                model=v.get("model") or None,
            ),
        )

    def scout(self) -> ScoutConfig:
        profile = self._yaml("configs/profile.yaml")
        s = self.settings().scout
        return ScoutConfig(
            title_filter=profile.get("scout_filters", {}),
            tracked_companies=self._load_companies(),
            worker_count=s.worker_count,
            max_pages=s.max_pages,
            respect_robots=s.respect_robots,
            model=s.model or os.environ.get("SCOUT_MODEL") or None,
        )

    def enrich(self, limit: int | None = None) -> EnrichConfig:
        s = self.settings().enrich
        return EnrichConfig(
            concurrency=s.concurrency,
            checkpoint_every=s.checkpoint_every,
            limit=limit,
            model=s.model or os.environ.get("ENRICH_MODEL") or None,
        )

    def evaluate(self) -> EvaluateConfig:
        s = self.settings().evaluate
        return EvaluateConfig(
            auto_reject_threshold=s.auto_reject_threshold,
            auto_match_threshold=s.auto_match_threshold,
            scoring_weights=s.scoring_weights,
            model=s.model or os.environ.get("EVALUATE_MODEL") or None,
        )

    def profile(self) -> dict:
        """Return the raw profile dict (used by Vetter and FeatureExtractor)."""
        return self._yaml("configs/profile.yaml")

    def _yaml(self, relative_path: str) -> dict:
        path = self._root / relative_path
        if not path.exists():
            return {}
        with path.open() as f:
            return yaml.safe_load(f) or {}

    def _load_companies(self) -> list[dict]:
        path = self._root / "configs" / "companies.json"
        if not path.exists():
            return []
        with path.open() as f:
            data = json.load(f)
        return [c for c in data.get("companies", []) if c.get("enabled", True)]
