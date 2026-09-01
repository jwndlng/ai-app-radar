"""TaskRegistry — tracking of background pipeline operations with file persistence."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TaskRecord:
    id: str
    operation: str
    status: str  # running | done | failed
    started_at: datetime
    finished_at: datetime | None = None
    result: dict | None = None
    error: str | None = None
    progress_current: int | None = None
    progress_total: int | None = None
    events: list[dict] = field(default_factory=list)

    # The list endpoint must not ship full event logs (100 records with
    # complete pipeline logs add up to tens of MB, polled every 5 seconds),
    # but the UI renders events for BOTH running and finished tasks from the
    # polled list — so finished tasks keep a short tail (summaries, failures)
    # rather than nothing.
    _SUMMARY_EVENTS_RUNNING = 100
    _SUMMARY_EVENTS_FINISHED = 20

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation": self.operation,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "result": self.result,
            "error": self.error,
            "progress_current": self.progress_current,
            "progress_total": self.progress_total,
            "events": self.events,
        }

    def to_summary_dict(self) -> dict:
        d = self.to_dict()
        if self.status in {"running", "cancelling"}:
            d["events"] = self.events[-self._SUMMARY_EVENTS_RUNNING:]
        else:
            d["events"] = self.events[-self._SUMMARY_EVENTS_FINISHED:]
        d["event_count"] = len(self.events)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> TaskRecord:
        return cls(
            id=d["id"],
            operation=d["operation"],
            status=d["status"],
            started_at=datetime.fromisoformat(d["started_at"]),
            finished_at=datetime.fromisoformat(d["finished_at"]) if d.get("finished_at") else None,
            result=d.get("result"),
            error=d.get("error"),
            progress_current=d.get("progress_current"),
            progress_total=d.get("progress_total"),
            events=d.get("events", []),
        )


class TaskRegistry:
    _MAX = 100
    # Cap events kept per task so records (and the persisted tasks.json,
    # rewritten on every flush) stay bounded instead of growing without limit.
    _MAX_EVENTS = 500

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        # No maxlen: eviction is manual so a still-running task is never
        # silently dropped (which would leave its run headless/uncancellable).
        self._records: deque[TaskRecord] = deque()
        self._cancel_events: dict[str, asyncio.Event] = {}
        if self._path and self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                for record_dict in reversed(data):
                    record = TaskRecord.from_dict(record_dict)
                    # Trim oversized histories written before the event cap
                    # existed; the next flush shrinks the file accordingly.
                    if len(record.events) > self._MAX_EVENTS:
                        record.events = record.events[-self._MAX_EVENTS:]
                    if record.status in {"running", "cancelling"}:
                        record.status = "cancelled"
                        record.finished_at = record.finished_at or datetime.now(timezone.utc)
                        record.error = "interrupted by server restart"
                    self._records.appendleft(record)
                self._evict()
            except Exception as exc:
                logger.warning("Could not load task history from %s: %s — starting empty", self._path, exc)

    def create(self, operation: str) -> str:
        task_id = uuid.uuid4().hex[:8]
        self._records.appendleft(
            TaskRecord(id=task_id, operation=operation, status="running", started_at=datetime.now(timezone.utc))
        )
        self._evict()
        self._flush()
        return task_id

    def _evict(self) -> None:
        """Drop oldest finished records beyond _MAX; running tasks are kept."""
        if len(self._records) <= self._MAX:
            return
        keep: list[TaskRecord] = []
        overflow = len(self._records) - self._MAX
        for record in reversed(self._records):
            if overflow > 0 and record.status not in {"running", "cancelling"}:
                overflow -= 1
                continue
            keep.append(record)
        self._records = deque(reversed(keep))

    def complete(self, task_id: str, result: dict | None = None) -> None:
        record = self._get(task_id)
        if record:
            record.status = "done"
            record.finished_at = datetime.now(timezone.utc)
            record.result = result
            self._flush()

    def update_progress(self, task_id: str, current: int, total: int) -> None:
        record = self._get(task_id)
        if record:
            record.progress_current = current
            record.progress_total = total

    def fail(self, task_id: str, error: str) -> None:
        record = self._get(task_id)
        if record:
            record.status = "failed"
            record.finished_at = datetime.now(timezone.utc)
            record.error = error
            self._flush()

    def get(self, task_id: str) -> TaskRecord | None:
        return self._get(task_id)

    def all(self) -> list[TaskRecord]:
        return list(self._records)

    def add_event(self, task_id: str, event: dict) -> None:
        record = self._get(task_id)
        if record:
            record.events.append(event)
            if len(record.events) > self._MAX_EVENTS:
                del record.events[: -self._MAX_EVENTS]

    def register_event(self, task_id: str, event: asyncio.Event) -> None:
        self._cancel_events[task_id] = event

    def unregister_event(self, task_id: str) -> None:
        self._cancel_events.pop(task_id, None)

    def cancel(self, task_id: str) -> bool:
        record = self._get(task_id)
        if record is None or record.status in {"done", "failed", "cancelled"}:
            return False
        event = self._cancel_events.get(task_id)
        if event:
            event.set()
        record.status = "cancelling"
        self._flush()
        return True

    def is_cancelled(self, task_id: str) -> bool:
        event = self._cancel_events.get(task_id)
        return event is not None and event.is_set()

    def mark_cancelled(self, task_id: str) -> None:
        record = self._get(task_id)
        if record:
            record.status = "cancelled"
            record.finished_at = datetime.now(timezone.utc)
            self._flush()

    def _get(self, task_id: str) -> TaskRecord | None:
        return next((r for r in self._records if r.id == task_id), None)

    def _flush(self) -> None:
        if self._path is None:
            return
        payload = json.dumps([r.to_dict() for r in self._records], indent=2)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._path.parent)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(payload)
            os.replace(tmp, self._path)
        except Exception:
            os.unlink(tmp)
            raise


def make_event_callback(registry: "TaskRegistry", task_id: str) -> Callable[[dict], None]:
    def on_event(event: dict) -> None:
        registry.add_event(task_id, event)
    return on_event


def make_progress_callback(registry: "TaskRegistry", task_id: str):
    def on_progress(current: int, total: int) -> None:
        registry.update_progress(task_id, current, total)
    return on_progress


async def run_with_tracking(registry: TaskRegistry, task_id: str, coro: Any) -> None:
    try:
        result = await coro
        if registry.is_cancelled(task_id):
            registry.mark_cancelled(task_id)
        else:
            registry.complete(task_id, result if isinstance(result, dict) else {"value": result})
    except asyncio.CancelledError:
        registry.mark_cancelled(task_id)
        raise
    except Exception as e:
        registry.fail(task_id, str(e))
    finally:
        registry.unregister_event(task_id)
