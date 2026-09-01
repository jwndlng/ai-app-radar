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
from notifications.notifier import NullNotifier, Notifier
from scout.state_tracker import StateTracker


class ScoutConsumer(BaseConsumer[dict]):
    def __init__(self, config: ScoutConfig, root_dir: Path, log: RunLogger,
                 notifier: Notifier = None) -> None:
        self._config = config
        self._root = root_dir
        self._log = log
        self._notifier = notifier if notifier is not None else NullNotifier()
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
        new_count = self._ingest()
        await self._notifier.on_scout_summary(new_count)

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
                # Self-heal: if a past enrichment overwrote the title with a
                # placeholder ('<UNKNOWN>', 'Multiple Open Roles …'), restore
                # the authoritative title from the ATS source.
                from enrich.consumer import _is_placeholder
                if title and _is_placeholder(existing.get("title")):
                    existing["title"] = title
                sources = existing.get("sources", [])
                if not any(s["url"] == url for s in sources):
                    sources.append(discovery_entry)
                    existing["sources"] = sources
                    # Only jobs still in "discovered" may have their canonical
                    # URL replaced; a job the user is already tracking through
                    # the pipeline must keep the URL it was enriched from.
                    if is_direct and existing.get("state", "discovered") == "discovered":
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

    def _ingest(self) -> int:
        if not self._discovered_pool:
            self._log.finish("no changes discovered")
            return 0

        # Build master_map from the tracker's already-loaded data instead of
        # re-reading applications.json from disk. known_jobs may index some jobs
        # under two keys (computed + stored id); deduplicate by computed id.
        seen_ids: set[str] = set()
        master_map: dict[str, dict] = {}
        url_to_id: dict[str, str] = {}
        for job in self._tracker.known_jobs.values():
            aid = self._tracker.generate_id(job.get("company", ""), job.get("title", ""))
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            master_map[aid] = job
            if job.get("url"):
                url_to_id[job["url"]] = aid

        store = ApplicationStore(self._root / "artifacts" / "applications.json")

        # URLs shared by several distinct pool entries (e.g. a careers-page
        # fallback URL) cannot identify a job — skip URL-based dedup for them,
        # or the second job would silently merge into (and vanish behind) the first.
        url_counts: dict[str, int] = {}
        for job in self._discovered_pool.values():
            if job.get("url"):
                url_counts[job["url"]] = url_counts.get(job["url"], 0) + 1

        new_count = 0
        updated_count = 0
        touched: list[dict] = []

        for jid, job in self._discovered_pool.items():
            url = job.get("url")
            url_match = url_to_id.get(url) if url and url_counts.get(url, 0) == 1 else None
            existing_id = url_match or (jid if jid in master_map else None)
            if existing_id:
                master_map[existing_id]["sources"] = job["sources"]
                if job.get("url") and not master_map[existing_id].get("url"):
                    master_map[existing_id]["url"] = job["url"]
                    if (master_map[existing_id].get("status") == "failed" and
                            "No URL" in master_map[existing_id].get("error_message", "")):
                        master_map[existing_id]["status"] = "ok"
                        master_map[existing_id].pop("error_message", None)
                StateMachine.touch_updated(master_map[existing_id])
                touched.append(master_map[existing_id])
                updated_count += 1
            else:
                master_map[jid] = job
                if job.get("url"):
                    url_to_id[job["url"]] = jid
                touched.append(job)
                new_count += 1

        # Save only jobs this run touched: re-saving the entire start-of-run
        # snapshot would overwrite concurrent edits made via the API.
        store.save(touched)
        self._log.finish(f"{new_count} new, {updated_count} updated")
        return new_count
