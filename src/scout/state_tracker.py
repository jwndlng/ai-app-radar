from __future__ import annotations

import re
from pathlib import Path

from core.store import ApplicationStore


class StateTracker:
    def __init__(self, root_dir: Path | str) -> None:
        self._root = Path(root_dir)
        self.known_jobs: dict[str, dict] = {}
        self.url_index: dict[str, dict] = {}
        self._load_state()

    def generate_id(self, company: str, title: str) -> str:
        """Return a stable unique ID based on normalised company + title."""
        c = re.sub(r"\W+", "", company.lower().strip())
        t = re.sub(r"\W+", "", title.lower().strip())
        return f"{c}-{t}"

    def get_existing_job(self, company: str, title: str) -> dict | None:
        return self.known_jobs.get(self.generate_id(company, title))

    def get_existing_by_url(self, url: str) -> dict | None:
        return self.url_index.get(url)

    def _load_state(self) -> None:
        try:
            store = ApplicationStore(self._root / "artifacts" / "radar.db")
            jobs = store.load()
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                url = job.get("url", "")
                if url:
                    self.url_index[url] = job
                jid_fresh = self.generate_id(job.get("company", ""), job.get("title", ""))
                jid_stored = job.get("id") or jid_fresh
                self.known_jobs[jid_fresh] = job
                self.known_jobs[jid_stored] = job
        except Exception as e:
            print(f"Warning: Could not load jobs in StateTracker: {e}")
