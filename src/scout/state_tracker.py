from __future__ import annotations

import json
import re
from pathlib import Path


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
        apps_json = self._root / "artifacts" / "applications.json"
        if not apps_json.exists():
            return
        try:
            with apps_json.open() as f:
                data = json.load(f)
            if not data:
                return
            for job in data:
                if not isinstance(job, dict):
                    continue
                url = job.get("url", "")
                if url:
                    self.url_index[url] = job
                jid_fresh = self.generate_id(job.get("company", ""), job.get("title", ""))
                # Index under both the re-computed key and the stored id so that
                # lookups succeed even when company/title formatting drifted over time.
                jid_stored = job.get("id") or jid_fresh
                self.known_jobs[jid_fresh] = job
                self.known_jobs[jid_stored] = job
        except Exception as e:
            print(f"Warning: Could not load applications.json: {e}")
