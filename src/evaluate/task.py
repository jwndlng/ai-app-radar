"""EvaluateTask — wires EvaluateProducer and EvaluateConsumer into the pipeline runtime."""

from __future__ import annotations

from pathlib import Path

from core.config import AppConfigLoader
from core.logger import RunLogger
from core.store import ApplicationStore
from core.task import BaseTask
from evaluate.fit_scorer import FitScorer
from evaluate.producer import EvaluateProducer
from evaluate.consumer import EvaluateConsumer
from evaluate.vetting import Vetter


class EvaluateTask(BaseTask[dict]):
    concurrency = 3
    checkpoint_every = 5
    start_gap: tuple[float, float] | None = None

    def __init__(self, root_dir: Path) -> None:
        loader = AppConfigLoader(root_dir)
        evaluate_config = loader.evaluate()
        profile = loader.profile()

        fit_scorer = FitScorer(weights=evaluate_config.scoring_weights, model=evaluate_config.model)
        profile_input = fit_scorer.build_profile_input(profile)
        vetter = Vetter(profile)

        store = ApplicationStore(root_dir / "artifacts" / "applications.json")
        all_apps = store.load()
        log = RunLogger("evaluate", root_dir)

        self._producer = EvaluateProducer(all_apps)
        self._consumer = EvaluateConsumer(
            all_apps=all_apps,
            store=store,
            fit_scorer=fit_scorer,
            profile_input=profile_input,
            vetter=vetter,
            auto_reject=evaluate_config.auto_reject_threshold,
            auto_match=evaluate_config.auto_match_threshold,
            location_reject=evaluate_config.location_reject_threshold,
            log=log,
        )

    @property
    def producer(self) -> EvaluateProducer:
        return self._producer

    @property
    def consumer(self) -> EvaluateConsumer:
        return self._consumer
