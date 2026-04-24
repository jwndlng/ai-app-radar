"""ScoutProducer — yields enabled company configs for scouting."""

from __future__ import annotations

from core.config import ScoutConfig
from core.task import BaseProducer


class ScoutProducer(BaseProducer[dict]):
    def __init__(self, config: ScoutConfig) -> None:
        self._config = config

    async def produce(self) -> list[dict]:
        return [c for c in self._config.tracked_companies if c.get("enabled", True)]
