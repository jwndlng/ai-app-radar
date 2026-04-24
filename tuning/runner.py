"""TuneRunner — runs scout against multiple models and judges the results."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tuning.case import CaseLoader, TuneCase
from tuning.judge import TuneJudge

_RESULTS_DIR = Path(__file__).parent / "results"


@dataclass
class ModelResult:
    model: str
    jobs: list[dict]
    page_count: int
    elapsed: float
    pages_pass: bool
    jobs_pass: bool
    url_pass: bool

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    @property
    def url_count(self) -> int:
        return sum(1 for j in self.jobs if j.get("url"))

    @property
    def url_coverage(self) -> float:
        return self.url_count / self.job_count if self.job_count else 1.0


class TuneRunner:
    def __init__(self, case: TuneCase) -> None:
        self._case = case

    async def run(self) -> None:
        print(f"\nTuning case : {self._case.company}")
        print(f"URL         : {self._case.careers_url}")
        print(f"Models      : {', '.join(self._case.models)}\n")

        results: list[ModelResult] = []
        for model in self._case.models:
            result = await self._run_model(model)
            results.append(result)

        judge_input = [
            {
                "model": r.model,
                "pages_visited": r.page_count,
                "jobs": [{"title": j["title"], "url": j.get("url", "")} for j in r.jobs],
            }
            for r in results
        ]
        print("\nRunning judge…")
        judge_result = await TuneJudge().judge(judge_input)

        self._write_jsonl(results, judge_result)
        self._print_table(results, judge_result)

    async def _run_model(self, model: str) -> ModelResult:
        from scout.providers.websearch import WebsearchProvider

        company_config = {
            "name": self._case.company,
            "careers_url": self._case.careers_url,
            "scan_method_config": self._case.scan_method_config,
        }
        provider = WebsearchProvider(model=model)
        print(f"  [{model}] scouting…")
        start = time.monotonic()
        jobs = await provider.scout(company_config, filters={})
        elapsed = time.monotonic() - start

        page_count = provider._last_page_count
        pages_pass = page_count >= self._case.expected_pages
        jobs_pass = self._case.jobs_min <= len(jobs) <= self._case.jobs_max
        url_count = sum(1 for j in jobs if j.get("url"))
        url_coverage = url_count / len(jobs) if jobs else 1.0
        url_pass = url_coverage >= self._case.url_coverage_min

        print(f"  [{model}] {len(jobs)} jobs, {url_count} with URL, {page_count} pages, {elapsed:.1f}s")
        return ModelResult(
            model=model,
            jobs=jobs,
            page_count=page_count,
            elapsed=elapsed,
            pages_pass=pages_pass,
            jobs_pass=jobs_pass,
            url_pass=url_pass,
        )

    def _write_jsonl(self, results: list[ModelResult], judge_result: object) -> None:
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = self._case.company.lower().replace(" ", "_")
        path = _RESULTS_DIR / f"{slug}_{ts}.jsonl"

        with path.open("w") as f:
            for r in results:
                record = {
                    "type": "model_result",
                    "model": r.model,
                    "jobs": r.jobs,
                    "page_count": r.page_count,
                    "job_count": r.job_count,
                    "url_count": r.url_count,
                    "url_coverage": round(r.url_coverage, 3),
                    "pages_pass": r.pages_pass,
                    "jobs_pass": r.jobs_pass,
                    "url_pass": r.url_pass,
                    "elapsed": round(r.elapsed, 2),
                }
                f.write(json.dumps(record) + "\n")

            from pydantic import BaseModel as _BM
            judge_record = {
                "type": "judge",
                **(judge_result.model_dump() if isinstance(judge_result, _BM) else vars(judge_result)),
            }
            f.write(json.dumps(judge_record) + "\n")

        print(f"\nResults written to: {path}")

    def _print_table(self, results: list[ModelResult], judge_result: object) -> None:
        col_w = max((len(r.model) for r in results), default=10)
        col_w = max(col_w, 30)

        header = (
            f"{'Model':<{col_w}}  {'Pages':>5}  {'Jobs':>5}  {'URLs':>5}  "
            f"{'P-Pass':>6}  {'J-Pass':>6}  {'U-Pass':>6}  {'Elapsed':>8}"
        )
        sep = "─" * len(header)
        print(f"\n{sep}")
        print(header)
        print(sep)

        for r in results:
            p_flag = "✓" if r.pages_pass else "✗"
            j_flag = "✓" if r.jobs_pass else "✗"
            u_flag = "✓" if r.url_pass else "✗"
            print(
                f"{r.model:<{col_w}}  {r.page_count:>5}  {r.job_count:>5}  {r.url_count:>5}  "
                f"{p_flag:>6}  {j_flag:>6}  {u_flag:>6}  {r.elapsed:>7.1f}s"
            )

        print(sep)
        consensus = getattr(judge_result, "consensus_count", "?")
        summary = getattr(judge_result, "summary", "")
        print(f"\nJudge consensus : {consensus} jobs")
        print(f"Summary         : {summary}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m tuning.runner <case-slug>", file=sys.stderr)
        sys.exit(1)

    _slug = sys.argv[1]
    _case = CaseLoader().load(_slug)
    asyncio.run(TuneRunner(_case).run())
