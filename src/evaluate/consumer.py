"""EvaluateConsumer — vets and LLM-scores a single enriched job."""

from __future__ import annotations

import time
from datetime import datetime

from core.logger import RunLogger
from core.state_machine import StateMachine
from core.store import ApplicationStore
from core.task import BaseConsumer
from evaluate.agent import FitResult
from evaluate.fit_scorer import FitScorer
from evaluate.vetting import Vetter


class EvaluateConsumer(BaseConsumer[dict]):
    # FitResult model fields + metadata written directly by this consumer.
    STATE_FIELDS: frozenset[str] = frozenset(FitResult.model_fields) | {
        "final_score", "matched_skills", "vetted_at", "rejection_reason", "archived_at",
    }
    def __init__(
        self,
        all_apps: list[dict],
        store: ApplicationStore,
        fit_scorer: FitScorer,
        profile_input: dict,
        vetter: Vetter,
        auto_reject: float,
        auto_match: float,
        location_reject: float,
        log: RunLogger,
    ) -> None:
        self._all_apps = all_apps
        self._store = store
        self._fit_scorer = fit_scorer
        self._profile_input = profile_input
        self._vetter = vetter
        self._auto_reject = auto_reject
        self._auto_match = auto_match
        self._location_reject = location_reject
        self._log = log
        self._reviewed = 0

    async def on_start(self, total: int) -> None:
        self._log.start(total=total)
        if total == 0:
            self._log.item_warn(
                "—", label="evaluate", detail="no parsed jobs — run enrich first"
            )

    async def consume(self, job: dict) -> None:
        name = f"{job.get('company', '?')} — {job.get('title', '?')}"
        t0 = time.monotonic()

        # Phase 1: location pre-filter
        passed, reason = self._vetter.vet(job)
        if not passed:
            self._archive_job(job, reason)
            self._log.item_warn(name, label="evaluate", detail=f"→ auto-reject [{reason}]",
                                elapsed=time.monotonic() - t0)
            return

        # Phase 2: LLM fit scoring
        try:
            scored = await self._fit_scorer.score(job, self._profile_input)
        except Exception as e:
            job["status"] = "failed"
            job["error_message"] = f"{type(e).__name__}: {e}"
            self._log.item_fail(name, label="evaluate", error=e,
                                elapsed=time.monotonic() - t0)
            return

        if scored is None:
            job["status"] = "failed"
            job["error_message"] = "fit scoring returned no result"
            self._log.item_fail(name, label="evaluate", error="fit scoring returned no result",
                                elapsed=time.monotonic() - t0)
            return

        result, matched_skills = scored
        final_score = self._fit_scorer.compute_final_score(result)

        # Location hard gate — reject before writing any scores
        if result.location_score <= self._location_reject:
            reason = result.location_reason or f"Location score {result.location_score}/10 below threshold"
            self._reject_job(job, reason)
            self._log.item_warn(name, label="evaluate",
                                detail=f"→ auto-reject [location hard-block: {reason}]",
                                elapsed=time.monotonic() - t0)
            return

        job["final_score"] = final_score
        job["score"] = result.score
        job["location_score"] = result.location_score
        job["seniority_score"] = result.seniority_score
        job["compensation_score"] = result.compensation_score
        job["archetype"] = result.archetype
        job["reasons"] = result.reasons
        job["location_reason"] = result.location_reason
        job["seniority_reason"] = result.seniority_reason
        job["compensation_reason"] = result.compensation_reason
        job["matched_skills"] = matched_skills
        elapsed = time.monotonic() - t0

        # Phase 3: threshold routing on final_score
        if final_score < self._auto_reject:
            self._archive_job(
                job, f"Score {final_score}/10 below auto-reject threshold ({self._auto_reject})"
            )
            self._log.item_warn(name, label="evaluate",
                                detail=f"→ auto-reject [score {final_score}/10 below threshold]",
                                elapsed=elapsed)
        elif final_score > self._auto_match:
            job["state"] = "match"
            job["status"] = "ok"
            job.pop("error_message", None)
            job["vetted_at"] = datetime.now().isoformat()
            StateMachine.touch_updated(job)
            self._reviewed += 1
            self._log.item_ok(name, label="evaluate",
                              detail=f"score {final_score}/10 → match [{'; '.join(result.reasons)}]",
                              elapsed=elapsed)
        else:
            job["state"] = "review"
            job["status"] = "ok"
            job.pop("error_message", None)
            job["vetted_at"] = datetime.now().isoformat()
            StateMachine.touch_updated(job)
            self._reviewed += 1
            self._log.item_ok(name, label="evaluate",
                              detail=f"score {final_score}/10 → review [{'; '.join(result.reasons)}]",
                              elapsed=elapsed)

    async def checkpoint(self) -> None:
        self._store.save(self._all_apps)

    async def finalize(self) -> None:
        self._store.save(self._all_apps)
        self._log.finish(f"{self._reviewed} jobs moved to match/review")

    @staticmethod
    def _archive_job(job: dict, reason: str) -> None:
        job["state"] = "archived"
        job["status"] = "ok"
        job["rejection_reason"] = reason
        job["archived_at"] = datetime.now().isoformat()
        StateMachine.touch_updated(job)
        job.pop("error_message", None)
        job.pop("jd", None)
        job.pop("jd_content", None)
        job.pop("description", None)

    @staticmethod
    def _reject_job(job: dict, reason: str) -> None:
        job["state"] = "rejected"
        job["status"] = "ok"
        job["rejection_reason"] = reason
        job["vetted_at"] = datetime.now().isoformat()
        StateMachine.touch_updated(job)
        job.pop("error_message", None)
