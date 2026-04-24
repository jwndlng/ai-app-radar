"""ApplicationStore — shared persistence layer for applications.json."""

from __future__ import annotations

import json
from pathlib import Path

_STATE_MIGRATION: dict[str, tuple[str, str]] = {
    "new": ("discovered", "ok"),
    "enriched": ("parsed", "ok"),
    "in_progress": ("match", "ok"),
    "review": ("review", "ok"),
    "archived": ("archived", "ok"),
    "applied": ("applied", "ok"),
}


class ApplicationStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open() as f:
            data = json.load(f)
        return [self._migrate(job) for job in data]

    def save(self, data: list[dict]) -> None:
        with self._path.open("w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _migrate(job: dict) -> dict:
        """Translate legacy single-field status to state + status."""
        if "state" in job:
            return job
        old_status = job.pop("status", "new")
        if old_status == "failed":
            job["state"] = "discovered"
            job["status"] = "failed"
            err = job.pop("enrich_error", None)
            if err:
                job["error_message"] = err
        else:
            state, status = _STATE_MIGRATION.get(old_status, ("discovered", "ok"))
            job["state"] = state
            job["status"] = status
        return job
