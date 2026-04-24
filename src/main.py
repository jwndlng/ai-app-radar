"""
Unified CLI entry point for the agentic application pipeline.

Usage:
  uv run python -m main <flow> [options]

Flows:
  scout                  Discover new roles from all configured sources
  enrich                 Extract metadata from discovered roles
  evaluate               Score and triage enriched roles
  sync                   Run the full pipeline: scout → enrich → evaluate
"""

from __future__ import annotations

from pathlib import Path

from cli import PipelineCLI

ROOT_DIR = Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    PipelineCLI(ROOT_DIR).run()
