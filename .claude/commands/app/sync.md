---
name: "App: Sync"
description: Run the full pipeline end-to-end — scout, enrich, evaluate, report
category: Workflow
tags: [workflow, pipeline, sync]
---

Run the full pipeline to check for anything new. Intended for use when the pipeline is in a known-good state and you want a fresh pass.

**Invocation**: `/app:sync`

---

## What this does

Runs all four stages in sequence, using the recommended mode for each:

```
Scout   →  Enrich (Gemini CLI, limit 20)  →  Evaluate (agent-native, limit 20)  →  Report
```

Limits are conservative by default to avoid burning quota on a first sync. If everything looks good, you can re-run individual stages without limits.

---

## Steps

// turbo
**Stage 1 — Scout** (discover new roles):
```bash
uv run python -m main scout
```

**Stage 2 — Enrich** (extract metadata, Gemini CLI batch):
```bash
uv run python -m main enrich --limit 20 --concurrency 5
```

**Stage 3 — Evaluate** (score against profile, agent-native):

After Stage 2 completes, run `/app:evaluate 20` — this uses Claude Code in-context for full reasoning per job.

**Stage 4 — Report** (generate dashboard):

After Stage 3 completes, run `/app:report`.

---

## After the run

- Open `artifacts/dashboard.html` in a browser.
- New `review` jobs are the ones worth looking at.
- Use the 8-char hash ID on any card to reference a job: *"update job `a1b2c3d4`"*.
- If a job's remote policy or location looks wrong, open the URL and verify — Greenhouse form dropdowns can leak into extracted fields.
