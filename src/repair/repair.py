"""Repair flow — scan recent logs for errors and reset retryable jobs."""

from __future__ import annotations

from pathlib import Path

from core.log_analyzer import LogAnalyzer, LogError
from core.store import ApplicationStore

_G = "\033[32m"
_Y = "\033[33m"
_R = "\033[31m"
_B = "\033[1m"
_X = "\033[0m"

_FLOWS = ["scout", "enrich", "evaluate"]


class RepairOrchestrator:
    def __init__(self, root_dir: Path, last_n: int = 3) -> None:
        self._root = root_dir
        self._last_n = last_n
        self._analyzer = LogAnalyzer(root_dir / "logs")

    def run(self) -> None:
        errors = self._analyzer.collect(_FLOWS, self._last_n)

        print(f"\n{_B}Error scan — last {self._last_n} logs per flow{_X}")

        real_errors: dict[str, list[LogError]] = {}
        for flow, errs in errors.items():
            deduped = self._dedupe(errs)
            real = [e for e in deduped if e.detail.strip().lower() != "no matches"]
            real_errors[flow] = real

        total = sum(len(v) for v in real_errors.values())
        if total == 0:
            print(f"  {_G}✓{_X} No errors found.")
            return

        self._print_summary(real_errors)

        if real_errors.get("enrich"):
            self._fix_enrich(real_errors["enrich"])

        if real_errors.get("evaluate"):
            count = len(real_errors["evaluate"])
            print(
                f"\n  ℹ  evaluate: {count} error(s)"
                " — jobs remain state='parsed'/status='failed'"
                " and will be retried on next evaluate run."
            )

        if real_errors.get("scout"):
            count = len(real_errors["scout"])
            print(
                f"\n  ℹ  scout: {count} error(s)"
                " — check company config or careers page availability."
            )

    @staticmethod
    def _dedupe(errors: list[LogError]) -> list[LogError]:
        seen: set[tuple[str, str]] = set()
        result: list[LogError] = []
        for err in errors:
            key = (err.name, err.detail[:60])
            if key not in seen:
                seen.add(key)
                result.append(err)
        return result

    def _print_summary(self, errors: dict[str, list[LogError]]) -> None:
        for flow, errs in errors.items():
            if not errs:
                print(f"  {_G}✓{_X} {flow}: no errors")
                continue
            fails = [e for e in errs if e.event == "item_fail"]
            warns = [e for e in errs if e.event == "item_warn"]
            parts = []
            if fails:
                parts.append(f"{_R}{len(fails)} fail(s){_X}")
            if warns:
                parts.append(f"{_Y}{len(warns)} warn(s){_X}")
            print(f"\n  {_R}✗{_X} {flow}: {', '.join(parts)}")
            for err in errs:
                label = f"{_R}FAIL{_X}" if err.event == "item_fail" else f"{_Y}WARN{_X}"
                detail = err.detail.split("\n")[0][:120] if err.detail else "—"
                print(f"    [{label}] {err.name}")
                print(f"           {detail}")

    def _fix_enrich(self, errors: list[LogError]) -> None:
        store = ApplicationStore(self._root / "artifacts" / "applications.json")
        all_apps = store.load()

        error_names = {e.name for e in errors}
        reset_count = 0

        for job in all_apps:
            if job.get("state") != "discovered" or job.get("status") != "failed":
                continue
            name = f"{job.get('company', '?')} — {job.get('title', '?')}"
            if name in error_names:
                job["status"] = "ok"
                job.pop("error_message", None)
                reset_count += 1

        if reset_count:
            store.save(all_apps)
            print(
                f"\n  {_G}✓{_X} enrich: {reset_count} failed job(s) reset"
                " — run 'make enrich' to retry."
            )
        else:
            print(
                f"\n  ℹ  enrich: errors found in logs but no matching failed jobs in store"
                " (may have been retried already)."
            )
