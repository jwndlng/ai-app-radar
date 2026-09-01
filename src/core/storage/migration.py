"""Legacy applications.json data migrator."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from core.storage.base import DatabaseProvider

logger = logging.getLogger(__name__)


class LegacyJsonMigrator:
    """Migrates records from legacy applications.json into the active database provider."""

    def __init__(self, root_dir: Path | str) -> None:
        self._root = Path(root_dir)

    def migrate_if_needed(self, provider: DatabaseProvider) -> int:
        """Import legacy applications.json if database is unpopulated."""
        json_path = self._root / "artifacts" / "applications.json"
        if not json_path.exists():
            return 0

        backup_path = self._root / "artifacts" / "applications.json.migrated.bak"

        existing_count = provider.count_all()
        if existing_count > 0:
            # The database is already populated (migrated under older code
            # that only copied the file): still move the legacy file out of
            # the way, or a later legitimately-emptied table would silently
            # re-import this stale snapshot.
            json_path.replace(backup_path)
            return 0

        try:
            with json_path.open() as f:
                data = json.load(f)

            if not isinstance(data, list) or not data:
                return 0

            # Deduplicate by id before batch inserting
            seen: dict[str, dict] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                jid = item.get("id")
                if not jid:
                    c = re.sub(r"\W+", "", (item.get("company") or "").lower().strip())
                    t = re.sub(r"\W+", "", (item.get("title") or "").lower().strip())
                    jid = f"{c}-{t}" if (c or t) else item.get("url")
                    if jid:
                        item["id"] = jid

                if jid:
                    seen[jid] = item

            jobs = list(seen.values())
            if not jobs:
                return 0

            provider.upsert_batch(jobs)

            # Move (not copy) the legacy file out of the way: if it stayed in
            # place, any later moment where the table legitimately empties
            # (archiver, manual deletes) would silently re-import this stale
            # snapshot and resurrect deleted jobs.
            json_path.replace(backup_path)

            logger.info("Migrated %d legacy job records from %s into database", len(jobs), json_path)
            return len(jobs)
        except Exception as exc:
            logger.error("Failed to migrate legacy applications.json: %s", exc)
            return 0

