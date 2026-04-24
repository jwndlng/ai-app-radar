"""LogAnalyzer — reads pipeline JSONL logs and extracts error events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LogError:
    flow: str
    name: str
    event: str
    detail: str
    ts: str


class LogAnalyzer:
    _ERROR_EVENTS = {"item_warn", "item_fail"}

    def __init__(self, logs_dir: Path) -> None:
        self._logs_dir = logs_dir

    def last_logs(self, flow: str, n: int = 3) -> list[Path]:
        return sorted(self._logs_dir.glob(f"{flow}_*.jsonl"))[-n:]

    def errors_from_file(self, path: Path) -> list[LogError]:
        errors: list[LogError] = []
        with path.open() as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("event") not in self._ERROR_EVENTS:
                    continue
                errors.append(LogError(
                    flow=entry.get("flow", ""),
                    name=entry.get("name", ""),
                    event=entry.get("event", ""),
                    detail=str(entry.get("detail") or entry.get("error") or ""),
                    ts=entry.get("ts", ""),
                ))
        return errors

    def collect(self, flows: list[str], n: int = 3) -> dict[str, list[LogError]]:
        return {
            flow: [
                err
                for log_file in self.last_logs(flow, n)
                for err in self.errors_from_file(log_file)
            ]
            for flow in flows
        }
