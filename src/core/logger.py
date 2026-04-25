"""Universal structured logger for pipeline flows.

Each flow instantiates RunLogger with its name:

    log = RunLogger("scout", root_dir)
    log.start(total=190)
    log.item_ok("Acme Corp", label="greenhouse_api", detail="2 found", elapsed=0.4)
    log.item_warn("Cisco", label="agent_review", detail="no matches", elapsed=12.1)
    log.item_fail("Fortinet", label="agent_review", error=exc, tb=traceback.format_exc())
    log.finish("12 new, 8 updated")

Console output is colored ANSI. Log files are written to logs/<flow>_<ts>.jsonl as
JSON Lines — one event object per line — so they are streamingly safe and jq-queryable.

    jq 'select(.event=="item_fail")'         logs/scout_*.jsonl
    jq 'select(.event=="item_ok") | .detail' logs/enrich_*.jsonl
"""

from __future__ import annotations

import json
import time
import traceback as tb_module
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# ── ANSI codes (no external dependencies) ─────────────────────────────────────

_G = "\033[32m"   # green
_R = "\033[31m"   # red
_Y = "\033[33m"   # yellow
_C = "\033[36m"   # cyan
_D = "\033[2m"    # dim
_B = "\033[1m"    # bold
_X = "\033[0m"    # reset

_NAME_W = 40
_LABEL_W = 22


class RunLogger:
    """Colored console + streaming JSONL file logger for a single pipeline run."""

    def __init__(self, flow: str, root_dir: Path, on_event: Callable[[dict], None] | None = None) -> None:
        self._flow = flow
        self._root = root_dir
        self._on_event = on_event
        self._start_ts = datetime.now()
        self._start_mono = time.monotonic()
        self._total = 0
        self._ok = 0
        self._warn = 0
        self._fail = 0

        logs_dir = root_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        ts = self._start_ts.strftime("%Y-%m-%d_%H%M%S")
        self._log_path = logs_dir / f"{flow}_{ts}.jsonl"
        self._fh = self._log_path.open("a", encoding="utf-8")

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, total: int) -> None:
        """Print run header and emit run_start event."""
        self._total = total
        ts = self._start_ts.strftime("%Y-%m-%d %H:%M")
        print(f"\n{_B}{self._flow.capitalize()}{_X}  {_D}{ts}{_X}  —  {total} items\n")
        self._emit("run_start", total=total)

    def item_ok(
        self,
        name: str,
        label: str = "",
        detail: str = "",
        elapsed: float = 0.0,
        **extra: Any,
    ) -> None:
        """Green ✓ — item completed successfully."""
        self._ok += 1
        badge = f"{_G}✓{_X}"
        count = f"{_G}{detail}{_X}" if detail else ""
        self._print_item(badge, label, name, count, elapsed)
        self._emit("item_ok", name=name, label=label, detail=detail,
                   elapsed=round(elapsed, 2), **extra)

    def item_warn(
        self,
        name: str,
        label: str = "",
        detail: str = "",
        elapsed: float = 0.0,
        **extra: Any,
    ) -> None:
        """Dim ○ — completed but no actionable results."""
        self._warn += 1
        badge = f"{_D}○{_X}"
        count = f"{_D}{detail or '—'}{_X}"
        self._print_item(badge, label, name, count, elapsed)
        self._emit("item_warn", name=name, label=label, detail=detail,
                   elapsed=round(elapsed, 2), **extra)

    def item_fail(
        self,
        name: str,
        label: str = "",
        error: BaseException | str = "",
        tb: str = "",
        elapsed: float = 0.0,
        **extra: Any,
    ) -> None:
        """Red ✗ — item failed with an exception."""
        self._fail += 1
        err_str = f"{type(error).__name__}: {error}" if isinstance(error, BaseException) else str(error)
        badge = f"{_R}✗{_X}"
        count = f"{_R}{err_str}{_X}"
        self._print_item(badge, label, name, count, elapsed)
        self._emit("item_fail", name=name, label=label, error=err_str,
                   traceback=tb, elapsed=round(elapsed, 2), **extra)

    def finish(self, summary: str = "") -> None:
        """Print summary, emit run_end, flush and close the log file."""
        elapsed = time.monotonic() - self._start_mono
        total = self._ok + self._warn + self._fail

        print()
        ok_str   = f"{_G}{self._ok} ok{_X}"
        warn_str = f"{_D}{self._warn} empty{_X}"
        fail_str = f"{_R}{self._fail} failed{_X}" if self._fail else f"{_D}0 failed{_X}"
        print(f"  {_B}Done{_X} in {elapsed:.0f}s  —  {ok_str},  {warn_str},  {fail_str}")
        if summary:
            print(f"  {_C}→ {summary}{_X}")
        rel = self._log_path.relative_to(self._root)
        print(f"\n  {_D}Log → {rel}{_X}\n")

        self._emit("run_end", elapsed=round(elapsed, 2), summary=summary,
                   ok=self._ok, warn=self._warn, fail=self._fail, total=total)
        self._fh.flush()
        self._fh.close()

    # ── Internals ──────────────────────────────────────────────────────────────

    def _print_item(self, badge: str, label: str, name: str, detail: str, elapsed: float) -> None:
        current = self._ok + self._warn + self._fail
        w = len(str(self._total))
        progress = f"{_D}{current:{w}}/{self._total}{_X}" if self._total else ""
        label_col = f"[{label}]" if label else ""
        ts = f"{_D}{datetime.now().strftime('%H:%M:%S')}{_X}"
        print(
            f"  {badge} {ts}  {progress}  {_D}{label_col:{_LABEL_W}}{_X}"
            f" {name[:_NAME_W]:<{_NAME_W}}"
            f"  {detail}  {_D}{elapsed:.1f}s{_X}"
        )

    def _emit(self, event: str, **fields: Any) -> None:
        record = {
            "event": event,
            "flow": self._flow,
            "ts": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()
        if self._on_event:
            self._on_event(record)
