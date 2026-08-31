"""EnrichProducer — yields new jobs from the application store."""

from __future__ import annotations

from core.task import BaseProducer

_MAX_ENRICH_ATTEMPTS = 3


class EnrichProducer(BaseProducer[dict]):
    def __init__(self, all_apps: list[dict]) -> None:
        self._all_apps = all_apps

    async def produce(self) -> list[dict]:
        # Skip jobs that have repeatedly failed enrichment (dead/expired
        # listings) so they don't burn fetch + LLM cost on every run.
        # repair.py resets the counter to make them eligible again.
        return [
            j for j in self._all_apps
            if j.get("state") == "discovered"
            and j.get("enrich_attempts", 0) < _MAX_ENRICH_ATTEMPTS
        ]
