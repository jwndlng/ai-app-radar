"""SQLite storage provider implementation with WAL mode, hybrid schema, and query projections."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from core.storage.base import DatabaseProvider

_SUMMARY_COLUMNS: tuple[str, ...] = (
    "id",
    "hash_id",
    "company",
    "title",
    "url",
    "location",
    "state",
    "status",
    "final_score",
    "location_score",
    "seniority_score",
    "favorited",
    "discovered_at",
    "updated_at",
    "vetted_at",
    "archived_at",
    "error_message",
)

_KNOWN_COLUMNS: frozenset[str] = frozenset(_SUMMARY_COLUMNS)

# Fields that live in the data JSON blob but that the job-list UI renders on
# collapsed cards; exposed in the summary projection via json_extract. They are
# not real columns, so they must stay out of _KNOWN_COLUMNS.
_SUMMARY_DATA_FIELDS: tuple[str, ...] = ("score", "salary_range", "compensation_score")

_SORT_COLUMNS: dict[str, str] = {
    "score": "final_score",
    "final_score": "final_score",
    "updated_at": "updated_at",
    "discovered_at": "discovered_at",
    "title": "title",
    "company": "company",
}

_STATE_MIGRATION: dict[str, tuple[str, str]] = {
    "new": ("discovered", "ok"),
    "enriched": ("parsed", "ok"),
    "in_progress": ("match", "ok"),
    "review": ("review", "ok"),
    "archived": ("archived", "ok"),
    "applied": ("applied", "ok"),
}


class SQLiteStorageProvider(DatabaseProvider):
    """Concrete SQLite implementation of DatabaseProvider with WAL mode and query projections."""

    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path) if isinstance(db_path, (str, Path)) else db_path
        self._is_memory = str(self._path) == ":memory:"
        self._memory_conn: sqlite3.Connection | None = None
        if self._is_memory:
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        self.initialize()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        if self._is_memory:
            assert self._memory_conn is not None
            yield self._memory_conn
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self._path),
            timeout=10.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        # These PRAGMAs are per-connection (unlike WAL, which persists in the
        # database file); setting them only in initialize() left every working
        # connection on the defaults.
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create tables, indexes, and configure PRAGMAs."""
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id TEXT PRIMARY KEY,
                    hash_id TEXT,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    location TEXT,
                    state TEXT NOT NULL DEFAULT 'discovered',
                    status TEXT NOT NULL DEFAULT 'ok',
                    final_score REAL,
                    location_score REAL,
                    seniority_score REAL,
                    favorited INTEGER NOT NULL DEFAULT 0,
                    discovered_at TEXT,
                    updated_at TEXT,
                    vetted_at TEXT,
                    archived_at TEXT,
                    error_message TEXT,
                    data TEXT NOT NULL DEFAULT '{}'
                );
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_state ON applications(state);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_url ON applications(url);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_company ON applications(company);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_updated_at ON applications(updated_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_final_score ON applications(final_score);")
            conn.commit()

    def close(self) -> None:
        if self._memory_conn:
            self._memory_conn.close()
            self._memory_conn = None

    def get_by_id(self, job_id: str) -> dict | None:
        if not job_id:
            return None
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM applications WHERE id = ? LIMIT 1;", (job_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row, full=True) if row else None

    def get_by_url(self, url: str) -> dict | None:
        if not url:
            return None
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM applications WHERE url = ? LIMIT 1;", (url,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row, full=True) if row else None

    def list_jobs(
        self,
        state: str | None = None,
        status: str | None = None,
        search: str | None = None,
        favorited_only: bool = False,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        projection: str = "summary",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict]:
        is_summary = projection == "summary"
        if is_summary:
            select_cols = ", ".join(_SUMMARY_COLUMNS)
            select_cols += ", " + ", ".join(
                f"json_extract(data, '$.{f}') AS {f}" for f in _SUMMARY_DATA_FIELDS
            )
        else:
            select_cols = "*"
        query = f"SELECT {select_cols} FROM applications"
        params: list[object] = []
        clauses: list[str] = []

        if state is not None and state != "all":
            clauses.append("state = ?")
            params.append(state)
        if status is not None and status != "all":
            clauses.append("status = ?")
            params.append(status)
        if favorited_only:
            clauses.append("favorited = 1")
        if search and search.strip():
            search_param = f"%{search.strip().lower()}%"
            clauses.append("(LOWER(title) LIKE ? OR LOWER(company) LIKE ? OR LOWER(COALESCE(location, '')) LIKE ?)")
            params.extend([search_param, search_param, search_param])

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        col_name = _SORT_COLUMNS.get(sort_by.lower(), "updated_at")
        direction = "ASC" if sort_order.lower() == "asc" else "DESC"
        query += f" ORDER BY {col_name} {direction} NULLS LAST"

        if limit is not None or offset > 0:
            # SQLite requires a LIMIT clause before OFFSET; -1 means unlimited.
            query += " LIMIT ?"
            params.append(limit if limit is not None else -1)
            if offset > 0:
                query += " OFFSET ?"
                params.append(offset)

        with self._connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_dict(row, full=not is_summary) for row in cursor.fetchall()]

    def upsert(self, job: dict) -> None:
        self.upsert_batch([job])

    def upsert_batch(self, jobs: list[dict]) -> None:
        if not jobs:
            return

        prepared_records = [self._dict_to_row_tuple(self._normalize_job(j)) for j in jobs]
        sql = """
            INSERT INTO applications (
                id, hash_id, company, title, url, location, state, status,
                final_score, location_score, seniority_score, favorited,
                discovered_at, updated_at, vetted_at, archived_at, error_message, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                hash_id = excluded.hash_id,
                company = excluded.company,
                title = excluded.title,
                url = excluded.url,
                location = excluded.location,
                state = excluded.state,
                status = excluded.status,
                final_score = excluded.final_score,
                location_score = excluded.location_score,
                seniority_score = excluded.seniority_score,
                favorited = excluded.favorited,
                discovered_at = COALESCE(applications.discovered_at, excluded.discovered_at),
                updated_at = excluded.updated_at,
                vetted_at = excluded.vetted_at,
                archived_at = excluded.archived_at,
                error_message = excluded.error_message,
                data = excluded.data;
        """

        with self._connection() as conn:
            conn.executemany(sql, prepared_records)
            conn.commit()

    def delete(self, job_id: str) -> bool:
        if not job_id:
            return False
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM applications WHERE id = ?;", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_state_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {
            "total": 0,
            "discovered": 0,
            "parsed": 0,
            "match": 0,
            "review": 0,
            "applied": 0,
            "rejected": 0,
            "archived": 0,
            "failed": 0,
        }

        with self._connection() as conn:
            cursor = conn.execute("SELECT state, count(*) as count FROM applications GROUP BY state;")
            for row in cursor.fetchall():
                st = row["state"]
                cnt = row["count"]
                counts["total"] += cnt
                if st in counts:
                    counts[st] = cnt

            fail_cursor = conn.execute("SELECT count(*) as count FROM applications WHERE status = 'failed';")
            fail_row = fail_cursor.fetchone()
            if fail_row:
                counts["failed"] = fail_row["count"]

        return counts

    def count_all(self) -> int:
        with self._connection() as conn:
            cursor = conn.execute("SELECT count(*) as count FROM applications;")
            row = cursor.fetchone()
            return row["count"] if row else 0

    @staticmethod
    def _normalize_job(job: dict) -> dict:
        """Translate legacy fields and ensure id, state, and status are well-formed."""
        job_copy = dict(job)
        if not job_copy.get("id"):
            c = re.sub(r"\W+", "", (job_copy.get("company") or "").lower().strip())
            t = re.sub(r"\W+", "", (job_copy.get("title") or "").lower().strip())
            job_copy["id"] = f"{c}-{t}" if (c or t) else (job_copy.get("url") or "unknown")

        if "state" not in job_copy:
            old_status = job_copy.pop("status", "new")
            if old_status == "failed":
                job_copy["state"] = "discovered"
                job_copy["status"] = "failed"
                err = job_copy.pop("enrich_error", None)
                if err:
                    job_copy["error_message"] = err
            else:
                state, status = _STATE_MIGRATION.get(old_status, ("discovered", "ok"))
                job_copy["state"] = state
                job_copy["status"] = status
        return job_copy

    @staticmethod
    def _dict_to_row_tuple(job: dict) -> tuple:
        extra_data = {k: v for k, v in job.items() if k not in _KNOWN_COLUMNS}
        favorited_int = 1 if job.get("favorited") else 0

        return (
            job.get("id"),
            job.get("hash_id"),
            job.get("company", ""),
            job.get("title", ""),
            job.get("url"),
            job.get("location"),
            job.get("state", "discovered"),
            job.get("status", "ok"),
            job.get("final_score"),
            job.get("location_score"),
            job.get("seniority_score"),
            favorited_int,
            job.get("discovered_at"),
            job.get("updated_at"),
            job.get("vetted_at"),
            job.get("archived_at"),
            job.get("error_message"),
            json.dumps(extra_data, ensure_ascii=False),
        )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row, full: bool = True) -> dict:
        out: dict = {}
        if full and "data" in row.keys():
            data_str = row["data"]
            try:
                out = json.loads(data_str) if data_str else {}
            except Exception:
                out = {}

        for col in row.keys():
            if col == "data":
                continue
            val = row[col]
            if col == "favorited":
                out["favorited"] = bool(val)
            elif val is not None:
                out[col] = val

        return out
