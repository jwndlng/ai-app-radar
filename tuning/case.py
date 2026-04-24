"""TuneCase dataclass and CaseLoader — load and validate YAML tune case files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_CASES_DIR = Path(__file__).parent / "cases"
_REQUIRED = ("company", "careers_url", "expected_pages", "jobs_min", "jobs_max", "models")


@dataclass
class TuneCase:
    company: str
    careers_url: str
    expected_pages: int
    jobs_min: int
    jobs_max: int
    models: list[str]
    scan_method_config: dict = field(default_factory=dict)
    url_coverage_min: float = 0.95


class CaseLoader:
    def load(self, slug: str) -> TuneCase:
        path = _CASES_DIR / f"{slug}.yaml"
        if not path.exists():
            available = [p.stem for p in _CASES_DIR.glob("*.yaml")]
            hint = f" Available cases: {', '.join(available)}" if available else ""
            raise FileNotFoundError(f"Case file not found: {path}.{hint}")

        with path.open() as f:
            data = yaml.safe_load(f) or {}

        missing = [k for k in _REQUIRED if k not in data]
        if missing:
            raise ValueError(f"Case '{slug}' is missing required fields: {', '.join(missing)}")

        return TuneCase(
            company=data["company"],
            careers_url=data["careers_url"],
            expected_pages=int(data["expected_pages"]),
            jobs_min=int(data["jobs_min"]),
            jobs_max=int(data["jobs_max"]),
            models=list(data["models"]),
            scan_method_config=data.get("scan_method_config", {}),
            url_coverage_min=float(data.get("url_coverage_min", 0.95)),
        )
