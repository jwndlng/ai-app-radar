"""EnrichConsumer — fetches and extracts metadata for a single job."""

from __future__ import annotations

import time
import traceback

from core.logger import RunLogger
from core.state_machine import StateMachine
from core.store import ApplicationStore
from core.task import BaseConsumer
from enrich.agent import EnrichResult

_MAX_JD_CHARS = 40_000

# Scout already sets title/company/location on discovered jobs; exclude them
# so undo from parsed does not wipe the original scout-provided values.
_SCOUT_FIELDS: frozenset[str] = frozenset({"title", "company", "location"})


class EnrichConsumer(BaseConsumer[dict]):
    STATE_FIELDS: frozenset[str] = frozenset(EnrichResult.model_fields) - _SCOUT_FIELDS

    def __init__(
        self,
        all_apps: list[dict],
        store: ApplicationStore,
        log: RunLogger,
        model: str | None = None,
    ) -> None:
        self._all_apps = all_apps
        self._store = store
        self._log = log
        self._model = model
        self._success = 0
        self._failed = 0

    async def on_start(self, total: int) -> None:
        self._log.start(total=total)
        if total == 0:
            self._log.item_warn(
                "—", label="enrich", detail="no discovered jobs — run scout first"
            )

    async def consume(self, job: dict) -> None:
        name = f"{job.get('company', '?')} — {job.get('title', '?')}"
        t0 = time.monotonic()
        try:
            enriched = await self._fetch_and_extract(job.get("url"))
            elapsed = time.monotonic() - t0
            if "_fetch_error" not in enriched:
                job.update(enriched)
                job["state"] = "parsed"
                job["status"] = "ok"
                job.pop("error_message", None)
                StateMachine.touch_updated(job)
                self._success += 1
                self._log.item_ok(name, label="enrich", detail="parsed", elapsed=elapsed)
            else:
                reason = enriched.get("_fetch_error", "unknown fetch error")[:120]
                self._mark_failed(job, reason)
                self._failed += 1
                self._log.item_warn(name, label="enrich", detail=reason, elapsed=elapsed)
        except Exception as e:
            elapsed = time.monotonic() - t0
            self._mark_failed(job, f"{type(e).__name__}: {e}")
            self._failed += 1
            self._log.item_fail(
                name, label="enrich", error=e, tb=traceback.format_exc(), elapsed=elapsed
            )

    async def checkpoint(self) -> None:
        self._store.save(self._all_apps)

    async def finalize(self) -> None:
        self._store.save(self._all_apps)
        self._log.finish(f"{self._success} parsed, {self._failed} failed")

    async def _fetch_and_extract(self, url: str | None) -> dict:
        if not url:
            return {"_fetch_error": "No URL available for this job"}
        try:
            page_text = await EnrichConsumer._fetch_page(url)
        except Exception as e:
            return {"_fetch_error": str(e)}

        if len(page_text.strip()) < 200:
            return {"_fetch_error": "Page returned insufficient content (SPA not rendered or empty)"}

        from enrich.agent import EnrichAgent
        result = await EnrichAgent(model=self._model).extract(page_text)
        if result.company.lower() in ("unknown", "", "n/a"):
            err = "Job page returned no valid content (soft 404 or expired listing)"
            return {"_fetch_error": err}
        return result.model_dump()

    @staticmethod
    async def _fetch_page(url: str) -> str:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            if response and response.status >= 400:
                await browser.close()
                raise RuntimeError(f"HTTP {response.status}")
            try:
                await page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass  # fall through with whatever rendered so far
            text = await page.locator("body").inner_text()
            await browser.close()
        return text[:_MAX_JD_CHARS]

    @staticmethod
    def _mark_failed(job: dict, reason: str) -> None:
        job["status"] = "failed"
        job["error_message"] = reason
