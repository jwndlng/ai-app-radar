"""EnrichProducer — yields new jobs from the application store."""

from __future__ import annotations

from core.task import BaseProducer


class EnrichProducer(BaseProducer[dict]):
    def __init__(self, all_apps: list[dict]) -> None:
        self._all_apps = all_apps

    async def produce(self) -> list[dict]:
        return [j for j in self._all_apps if j.get("state") == "discovered"]
