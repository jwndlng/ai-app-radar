"""EnrichTask — wires EnrichProducer and EnrichConsumer into the pipeline runtime."""

from __future__ import annotations

from pathlib import Path

from core.logger import RunLogger
from core.store import ApplicationStore
from core.task import BaseTask
from enrich.producer import EnrichProducer
from enrich.consumer import EnrichConsumer


class EnrichTask(BaseTask[dict]):
    concurrency = 5
    checkpoint_every = 5
    start_gap: tuple[float, float] | None = (0.25, 1.0)

    def __init__(self, root_dir: Path, limit: int | None = None, on_event=None) -> None:
        from core.config import AppConfigLoader
        cfg = AppConfigLoader(root_dir).enrich(limit=limit)
        self.concurrency = cfg.concurrency
        self.checkpoint_every = cfg.checkpoint_every
        if limit is not None:
            self.limit = limit

        store = ApplicationStore(root_dir / "artifacts" / "applications.json")
        all_apps = store.load()
        log = RunLogger("enrich", root_dir, on_event=on_event)

        self._producer = EnrichProducer(all_apps)
        self._consumer = EnrichConsumer(all_apps, store, log, model=cfg.model)

    @property
    def producer(self) -> EnrichProducer:
        return self._producer

    @property
    def consumer(self) -> EnrichConsumer:
        return self._consumer
