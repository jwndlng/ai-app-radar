"""PipelineRunner and shared FastAPI dependencies."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from fastapi import Request


def get_runner(request: Request):
    return request.app.state.runner


def get_registry(request: Request):
    return request.app.state.registry


class PipelineRunner:
    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    def _store(self):
        from core.store import ApplicationStore
        return ApplicationStore(self._root / "artifacts" / "applications.json")

    def _company_names(self) -> set[str]:
        from core.config import AppConfigLoader
        config = AppConfigLoader(self._root).scout()
        return {c.get("name", "").lower() for c in config.tracked_companies}

    def list_companies(self) -> list[dict]:
        path = self._root / "configs" / "companies.json"
        data = json.loads(path.read_text())
        return sorted(data.get("companies", []), key=lambda c: c.get("name", "").lower())

    def set_company_enabled(self, name: str, enabled: bool) -> bool:
        path = self._root / "configs" / "companies.json"
        data = json.loads(path.read_text())
        companies = data.get("companies", [])
        entry = next((c for c in companies if c.get("name", "").lower() == name.lower()), None)
        if entry is None:
            return False
        entry["enabled"] = enabled
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return True

    async def scout_all(self, on_progress: Callable[[int, int], None] | None = None) -> int:
        from core.config import AppConfigLoader
        from core.runtime import PipelineRuntime
        from scout.task import ScoutTask

        config = AppConfigLoader(self._root).scout()
        ids_before = {j["id"] for j in self._store().load()}
        await PipelineRuntime(ScoutTask(config, self._root)).run(on_progress=on_progress)
        return sum(1 for j in self._store().load() if j["id"] not in ids_before)

    async def scout_next(
        self, limit: int, on_progress: Callable[[int, int], None] | None = None
    ) -> int:
        from core.config import AppConfigLoader, ScoutConfig
        from core.runtime import PipelineRuntime
        from scout.task import ScoutTask

        config = AppConfigLoader(self._root).scout()
        filtered = ScoutConfig(
            title_filter=config.title_filter,
            tracked_companies=config.tracked_companies[:limit],
            max_pages=config.max_pages,
            respect_robots=config.respect_robots,
            model=config.model,
            worker_count=config.worker_count,
        )
        ids_before = {j["id"] for j in self._store().load()}
        await PipelineRuntime(ScoutTask(filtered, self._root)).run(on_progress=on_progress)
        return sum(1 for j in self._store().load() if j["id"] not in ids_before)

    async def scout_company(
        self, company_name: str, on_progress: Callable[[int, int], None] | None = None
    ) -> int | None:
        from core.config import AppConfigLoader, ScoutConfig
        from core.runtime import PipelineRuntime
        from scout.task import ScoutTask

        config = AppConfigLoader(self._root).scout()
        match = [c for c in config.tracked_companies if c.get("name", "").lower() == company_name.lower()]
        if not match:
            return None

        filtered = ScoutConfig(
            title_filter=config.title_filter,
            tracked_companies=match,
        )
        ids_before = {j["id"] for j in self._store().load()}
        await PipelineRuntime(ScoutTask(filtered, self._root)).run(on_progress=on_progress)
        return sum(1 for j in self._store().load() if j["id"] not in ids_before)

    async def enrich_all(self, on_progress: Callable[[int, int], None] | None = None) -> int:
        from core.runtime import PipelineRuntime
        from enrich.task import EnrichTask

        count = sum(1 for j in self._store().load() if j.get("state") == "discovered")
        await PipelineRuntime(EnrichTask(self._root)).run(on_progress=on_progress)
        return count

    async def enrich_next(
        self, limit: int = 10, on_progress: Callable[[int, int], None] | None = None
    ) -> int:
        from core.runtime import PipelineRuntime
        from enrich.task import EnrichTask

        available = sum(1 for j in self._store().load() if j.get("state") == "discovered")
        await PipelineRuntime(EnrichTask(self._root, limit=limit)).run(on_progress=on_progress)
        return min(limit, available)

    async def enrich_job(self, job_id: str) -> bool:
        from core.config import AppConfigLoader
        from core.logger import RunLogger
        from enrich.consumer import EnrichConsumer

        store = self._store()
        all_apps = store.load()
        job = next((j for j in all_apps if j.get("id") == job_id), None)
        if job is None:
            return False

        cfg = AppConfigLoader(self._root).enrich()
        log = RunLogger("enrich", self._root)
        consumer = EnrichConsumer(all_apps, store, log, model=cfg.model)
        await consumer.on_start(1)
        await consumer.consume(job)
        await consumer.finalize()
        return True

    async def evaluate_all(self, on_progress: Callable[[int, int], None] | None = None) -> int:
        from core.runtime import PipelineRuntime
        from evaluate.task import EvaluateTask

        count = sum(1 for j in self._store().load() if j.get("state") == "parsed")
        await PipelineRuntime(EvaluateTask(self._root)).run(on_progress=on_progress)
        return count

    async def evaluate_next(
        self, limit: int = 10, on_progress: Callable[[int, int], None] | None = None
    ) -> int:
        from core.runtime import PipelineRuntime
        from evaluate.task import EvaluateTask

        available = sum(1 for j in self._store().load() if j.get("state") == "parsed")
        task = EvaluateTask(self._root)
        task.limit = limit
        await PipelineRuntime(task).run(on_progress=on_progress)
        return min(limit, available)

    async def evaluate_job(self, job_id: str) -> bool:
        from core.config import AppConfigLoader
        from core.logger import RunLogger
        from evaluate.consumer import EvaluateConsumer
        from evaluate.fit_scorer import FitScorer
        from evaluate.vetting import Vetter

        store = self._store()
        all_apps = store.load()
        job = next((j for j in all_apps if j.get("id") == job_id), None)
        if job is None:
            return False

        loader = AppConfigLoader(self._root)
        evaluate_config = loader.evaluate()
        profile = loader.profile()
        fit_scorer = FitScorer(weights=evaluate_config.scoring_weights, model=evaluate_config.model)
        profile_input = fit_scorer.build_profile_input(profile)
        vetter = Vetter(profile)
        log = RunLogger("evaluate", self._root)

        consumer = EvaluateConsumer(
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
        await consumer.on_start(1)
        await consumer.consume(job)
        await consumer.finalize()
        return True

    async def run_job(self, job_id: str) -> list[str] | None:
        store = self._store()
        all_apps = store.load()
        job = next((j for j in all_apps if j.get("id") == job_id), None)
        if job is None:
            return None

        steps_run: list[str] = []
        state = job.get("state", "")

        if state == "discovered":
            await self.enrich_job(job_id)
            steps_run.append("enrich")
            refreshed = next((j for j in store.load() if j.get("id") == job_id), None)
            if refreshed and refreshed.get("state") == "parsed":
                await self.evaluate_job(job_id)
                steps_run.append("evaluate")
        elif state == "parsed":
            await self.evaluate_job(job_id)
            steps_run.append("evaluate")

        return steps_run

    # ── Settings management ───────────────────────────────────────────────────

    def _settings_path(self) -> Path:
        return self._root / "configs" / "settings.yaml"

    def load_settings(self) -> dict:
        import dataclasses
        from core.config import AppConfigLoader
        return dataclasses.asdict(AppConfigLoader(self._root).settings())

    def save_settings(self, data: dict) -> None:
        self._settings_path().write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
        )

    # ── Profile management ────────────────────────────────────────────────────

    def _profile_path(self) -> Path:
        return self._root / "configs" / "profile.yaml"

    def _backups_dir(self) -> Path:
        return self._root / "configs" / "backups"

    def load_profile(self) -> dict | None:
        path = self._profile_path()
        if not path.exists():
            return None
        return yaml.safe_load(path.read_text())

    def _backup_profile(self) -> None:
        path = self._profile_path()
        if not path.exists():
            return
        backups = self._backups_dir()
        backups.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        (backups / f"profile_{ts}.yaml").write_bytes(path.read_bytes())
        for old in sorted(backups.glob("profile_*.yaml"))[:-10]:
            old.unlink()

    def save_profile(self, data: dict) -> None:
        self._backup_profile()
        self._profile_path().write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
        )

    def list_backups(self) -> list[dict]:
        backups = self._backups_dir()
        if not backups.exists():
            return []
        files = sorted(backups.glob("profile_*.yaml"), reverse=True)
        result = []
        for f in files:
            mtime = f.stat().st_mtime
            created_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            result.append({"filename": f.name, "created_at": created_at})
        return result

    def restore_backup(self, filename: str) -> bool:
        backup_path = self._backups_dir() / filename
        if not backup_path.exists():
            return False
        self._backup_profile()
        self._profile_path().write_bytes(backup_path.read_bytes())
        return True

    def undo_job(self, job: dict) -> str | None:
        """Revert job to its previous state in-place. Returns new state, or None if not undoable."""
        from core.state_machine import StateMachine
        from enrich.consumer import EnrichConsumer
        from evaluate.consumer import EvaluateConsumer

        prev = StateMachine.prev_state(job)
        if prev is None:
            return None

        current = job["state"]

        if current == "parsed":
            for f in EnrichConsumer.STATE_FIELDS:
                job.pop(f, None)
        elif current in ("match", "review", "archived", "rejected", "applied") and prev == "parsed":
            for f in EvaluateConsumer.STATE_FIELDS:
                job.pop(f, None)

        job.pop("error_message", None)
        job.pop("prev_state", None)
        job["state"] = prev
        job["status"] = "ok"
        return prev
