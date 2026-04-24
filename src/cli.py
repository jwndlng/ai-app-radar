"""Pipeline CLI — argument parsing and flow dispatch."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


class PipelineCLI:
    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    def run(self) -> None:
        args = self._build_parser().parse_args()
        try:
            if args.flow == "scout":
                asyncio.run(self._run_scout(company=args.company))
            elif args.flow == "enrich":
                asyncio.run(self._run_enrich(
                    limit=args.limit,
                    concurrency=args.concurrency,
                    checkpoint_every=args.checkpoint_every,
                ))
            elif args.flow == "evaluate":
                asyncio.run(self._run_evaluate())
            elif args.flow == "sync":
                asyncio.run(self._run_sync())
            elif args.flow == "fix-errors":
                self._run_fix_errors(last_n=args.last_n)
            elif args.flow == "serve":
                self._run_serve(host=args.host, port=args.port)
        except Exception as e:
            print(f"\n[!] {args.flow} failed: {e}")
            sys.exit(1)

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="main",
            description="Agentic application pipeline",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        sub = parser.add_subparsers(dest="flow", metavar="flow")
        sub.required = True

        p_scout = sub.add_parser("scout", help="Discover new roles from all configured sources")
        p_scout.add_argument(
            "--company", type=str, default=None, metavar="NAME",
            help="Run scout for a single company only (case-insensitive match)",
        )

        p_enrich = sub.add_parser("enrich", help="Extract metadata from discovered roles")
        p_enrich.add_argument("--limit", type=int, default=None,
                              help="Max number of jobs to enrich (default: all)")
        p_enrich.add_argument("--concurrency", type=int, default=5,
                              help="Parallel workers (default: 5)")
        p_enrich.add_argument("--checkpoint-every", type=int, default=5,
                              dest="checkpoint_every",
                              help="Save every N completions (default: 5)")

        sub.add_parser("evaluate", help="Score and triage enriched roles")
        sub.add_parser("sync", help="Run the full pipeline: scout → enrich → evaluate")

        p_fix = sub.add_parser("fix-errors", help="Scan recent logs for errors and reset retryable jobs")
        p_fix.add_argument("--last-n", type=int, default=3, dest="last_n",
                           help="Number of recent log files per flow to scan (default: 3)")

        p_serve = sub.add_parser("serve", help="Start the API server")
        p_serve.add_argument("--host", type=str, default="127.0.0.1",
                             help="Bind host (default: 127.0.0.1)")
        p_serve.add_argument("--port", type=int, default=8000,
                             help="Bind port (default: 8000)")

        return parser

    async def _run_scout(self, company: str | None = None) -> None:
        from core.config import AppConfigLoader, ScoutConfig
        from core.runtime import PipelineRuntime
        from scout.task import ScoutTask

        config = AppConfigLoader(self._root).scout()

        if company:
            match = [c for c in config.tracked_companies if c.get("name", "").lower() == company.lower()]
            if not match:
                print(f"[-] No company named {company!r} found in configs/companies.json")
                sys.exit(1)
            config = ScoutConfig(
                title_filter=config.title_filter,
                tracked_companies=match,
            )
            print(f"[*] Scoping scout to: {match[0]['name']}")

        await PipelineRuntime(ScoutTask(config, self._root)).run()

    async def _run_enrich(
        self,
        limit: int | None = None,
        concurrency: int = 5,
        checkpoint_every: int = 5,
    ) -> None:
        from core.runtime import PipelineRuntime
        from enrich.task import EnrichTask
        await PipelineRuntime(
            EnrichTask(self._root, limit=limit, concurrency=concurrency,
                       checkpoint_every=checkpoint_every)
        ).run()

    async def _run_evaluate(self) -> None:
        from core.runtime import PipelineRuntime
        from evaluate.task import EvaluateTask
        await PipelineRuntime(EvaluateTask(self._root)).run()

    def _run_fix_errors(self, last_n: int = 3) -> None:
        from repair.repair import RepairOrchestrator
        RepairOrchestrator(self._root, last_n=last_n).run()

    def _run_serve(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        import uvicorn
        uvicorn.run("api.app:app", host=host, port=port)

    async def _run_sync(self) -> None:
        print("[sync] Starting full pipeline...")
        print("\n[sync] Step 1/3: Scout")
        await self._run_scout()
        print("\n[sync] Step 2/3: Enrich")
        await self._run_enrich()
        print("\n[sync] Step 3/3: Evaluate")
        await self._run_evaluate()
        print("\n[sync] Pipeline complete.")
