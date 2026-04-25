"""TaskRegistry — in-memory tracking of background pipeline operations."""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


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


class TaskRegistry:
    _MAX = 100

    def __init__(self) -> None:
        self._records: deque[TaskRecord] = deque(maxlen=self._MAX)

    def create(self, operation: str) -> str:
        task_id = uuid.uuid4().hex[:8]
        self._records.appendleft(
            TaskRecord(id=task_id, operation=operation, status="running", started_at=datetime.now(timezone.utc))
        )
        return task_id

    def complete(self, task_id: str, result: dict | None = None) -> None:
        record = self._get(task_id)
        if record:
            record.status = "done"
            record.finished_at = datetime.now(timezone.utc)
            record.result = result

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

    def get(self, task_id: str) -> TaskRecord | None:
        return self._get(task_id)

    def all(self) -> list[TaskRecord]:
        return list(self._records)

    def add_event(self, task_id: str, event: dict) -> None:
        record = self._get(task_id)
        if record:
            record.events.append(event)

    def _get(self, task_id: str) -> TaskRecord | None:
        return next((r for r in self._records if r.id == task_id), None)


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
        registry.complete(task_id, result if isinstance(result, dict) else {"value": result})
    except Exception as e:
        registry.fail(task_id, str(e))
