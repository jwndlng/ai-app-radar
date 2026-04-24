"""ScoutTask — wires ScoutProducer and ScoutConsumer into the pipeline runtime."""

from __future__ import annotations

from pathlib import Path

from core.config import ScoutConfig
from core.logger import RunLogger
from core.task import BaseTask
from scout.producer import ScoutProducer
from scout.consumer import ScoutConsumer


class ScoutTask(BaseTask[dict]):
    checkpoint_every = 1
    start_gap: tuple[float, float] | None = None

    def __init__(self, config: ScoutConfig, root_dir: Path) -> None:
        self.concurrency = config.worker_count
        log = RunLogger("scout", root_dir)
        self._producer = ScoutProducer(config)
        self._consumer = ScoutConsumer(config, root_dir, log)

    @property
    def producer(self) -> ScoutProducer:
        return self._producer

    @property
    def consumer(self) -> ScoutConsumer:
        return self._consumer
