"""ScoutConsumer — scans one company and ingests all discoveries on finalize."""

from __future__ import annotations

import hashlib
import time
import traceback
from datetime import datetime
from pathlib import Path

from core.config import ScoutConfig
from core.logger import RunLogger
from core.state_machine import StateMachine
from core.store import ApplicationStore
from core.task import BaseConsumer
from scout.providers.ashby import AshbyProvider
from scout.providers.greenhouse import GreenhouseProvider
from scout.providers.http import HttpProvider
from scout.providers.lever import LeverProvider
from scout.providers.scraper import ScraperProvider
from scout.providers.smartrecruiters import SmartRecruitersProvider
from scout.providers.websearch import WebsearchProvider
from scout.providers.workable import WorkableProvider
from scout.providers.workday import WorkdayProvider
from scout.state_tracker import StateTracker


class ScoutConsumer(BaseConsumer[dict]):
    def __init__(self, config: ScoutConfig, root_dir: Path, log: RunLogger) -> None:
        self._config = config
        self._root = root_dir
        self._log = log
        self._filters = config.title_filter
        self._tracker = StateTracker(root_dir)
        self._discovered_pool: dict[str, dict] = {}

        self._greenhouse = GreenhouseProvider()
        self._scraper = ScraperProvider()
        self._http = HttpProvider()
        self._ashby = AshbyProvider()
        self._lever = LeverProvider()
        self._workable = WorkableProvider()
        self._workday = WorkdayProvider()
        self._smartrecruiters = SmartRecruitersProvider()
        self._websearch = WebsearchProvider(
            model=config.model,
            max_pages=config.max_pages,
            respect_robots=config.respect_robots,
        )

    async def on_start(self, total: int) -> None:
        self._log.start(total)

    async def consume(self, company: dict) -> None:
        name = company.get("name", "?")
        method = company.get("scan_method", "playwright")
        t0 = time.monotonic()
        try:
            discovered = await self._dispatch(company, method)
            self._process_discovered(discovered, name, is_direct=True)
            elapsed = time.monotonic() - t0
            count = len(discovered)
            if count:
                self._log.item_ok(name, label=method, detail=f"{count} found", elapsed=elapsed)
            else:
                self._log.item_warn(name, label=method, detail="no matches", elapsed=elapsed)
        except Exception as e:
            elapsed = time.monotonic() - t0
            self._log.item_fail(
                name, label=method, error=e, tb=traceback.format_exc(), elapsed=elapsed
            )

    async def checkpoint(self) -> None:
        pass

    async def finalize(self) -> None:
        self._ingest()

    async def _dispatch(self, company: dict, method: str) -> list[dict]:
        if method == "greenhouse_api":
            return await self._greenhouse.scout(company, self._filters)
        if method == "http":
            return await self._http.scout(company, self._filters)
        if method in ("playwright", "scraper"):
            return await self._scraper.scout(company, self._filters)
        if method == "ashby_api":
            return await self._ashby.scout(company, self._filters)
        if method == "lever_api":
            return await self._lever.scout(company, self._filters)
        if method == "workable_api":
            return await self._workable.scout(company, self._filters)
        if method == "workday_api":
            return await self._workday.scout(company, self._filters)
        if method == "smartrecruiters_api":
            return await self._smartrecruiters.scout(company, self._filters)
        if method == "agent_review":
            return await self._websearch.scout(company, self._filters)
        return []

    def _process_discovered(
        self, jobs: list[dict], source_name: str, is_direct: bool = False
    ) -> None:
        for job in jobs:
            company = job.get("company", "")
            title = job.get("title", "")
            if not company or not title:
                continue
            jid = self._tracker.generate_id(company, title)
            url = job.get("url", "")
            existing = (
                self._tracker.get_existing_by_url(url)
                or self._tracker.get_existing_job(company, title)
                or self._discovered_pool.get(jid)
            )

            discovery_entry = {
                "source": source_name,
                "url": url,
                "discovered_at": datetime.now().isoformat(),
            }

            if existing:
                sources = existing.get("sources", [])
                if not any(s["url"] == url for s in sources):
                    sources.append(discovery_entry)
                    existing["sources"] = sources
                    if is_direct:
                        existing["url"] = url
                self._discovered_pool[jid] = existing
            else:
                job["id"] = jid
                job["hash_id"] = hashlib.sha1(jid.encode()).hexdigest()[:8]
                job["sources"] = [discovery_entry]
                job["discovered_at"] = discovery_entry["discovered_at"]
                job["state"] = "discovered"
                job["status"] = "ok"
                StateMachine.touch_updated(job)
                self._discovered_pool[jid] = job

    def _ingest(self) -> None:
        if not self._discovered_pool:
            self._log.finish("no changes discovered")
            return

        store = ApplicationStore(self._root / "artifacts" / "applications.json")
        all_apps = store.load()

        master_map: dict[str, dict] = {}
        url_to_id: dict[str, str] = {}
        for app in all_apps:
            aid = self._tracker.generate_id(app.get("company", ""), app.get("title", ""))
            master_map[aid] = app
            if app.get("url"):
                url_to_id[app["url"]] = aid

        new_count = 0
        updated_count = 0

        for jid, job in self._discovered_pool.items():
            existing_id = url_to_id.get(job.get("url")) or (jid if jid in master_map else None)
            if existing_id:
                master_map[existing_id]["sources"] = job["sources"]
                if job.get("url") and not master_map[existing_id].get("url"):
                    master_map[existing_id]["url"] = job["url"]
                    if (master_map[existing_id].get("status") == "failed" and
                            "No URL" in master_map[existing_id].get("error_message", "")):
                        master_map[existing_id]["status"] = "ok"
                        master_map[existing_id].pop("error_message", None)
                StateMachine.touch_updated(master_map[existing_id])
                updated_count += 1
            else:
                master_map[jid] = job
                if job.get("url"):
                    url_to_id[job["url"]] = jid
                new_count += 1

        store.save(list(master_map.values()))
        self._log.finish(f"{new_count} new, {updated_count} updated")
