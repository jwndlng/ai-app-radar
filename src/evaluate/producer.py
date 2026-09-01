"""EvaluateProducer — yields enriched jobs from the application store."""

from __future__ import annotations

from core.task import BaseProducer

_MAX_EVALUATE_ATTEMPTS = 3


class EvaluateProducer(BaseProducer[dict]):
    def __init__(self, all_apps: list[dict]) -> None:
        self._all_apps = all_apps

    async def produce(self) -> list[dict]:
        # Skip jobs whose scoring has repeatedly failed so they don't burn
        # LLM cost on every run; the archiver cleans them up after
        # failed_after_days.
        return [
            j for j in self._all_apps
            if j.get("state") == "parsed"
            and j.get("evaluate_attempts", 0) < _MAX_EVALUATE_ATTEMPTS
        ]
