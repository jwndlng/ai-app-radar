---
name: "Ops: Fix Pipeline Errors"
description: Scan recent pipeline logs, diagnose errors, propose and apply fixes — including code changes where needed
category: Ops
tags: [ops, logs, repair, pipeline]
---

Scan the last 3 log files for each of **scout**, **enrich**, and **evaluate**. Diagnose errors, classify them, propose fixes (including code fixes where needed), and apply them after confirmation.

**Invocation**: `/ops:fix-pipeline-errors [--last-n N]`

`--last-n N` — how many recent log files per flow to scan (default: 3)

---

## Phase 1 — Read & Deduplicate

Log files live in `logs/` as JSONL, named `{flow}_{date}_{time}.jsonl`.

For each flow (scout, enrich, evaluate):
- Find the last N files matching `logs/{flow}_*.jsonl` (sort by filename, take last N)
- Parse every line as JSON
- Collect events where `"event"` is `"item_warn"` or `"item_fail"`
- Deduplicate by `(name, detail[:60])` — same error across repeated runs counts once

Filter out scout `"no matches"` warnings — these are expected, not errors.

---

## Phase 2 — Diagnose & Classify

For every deduplicated error, assign a **fix class**:

| Error pattern | Fix class |
|---|---|
| `HTTP 503` / `HTTP 502` / `HTTP 429` | **data:transient** — reset to retry |
| `Timeout 60000ms exceeded` | **data:transient** — reset to retry |
| `ERR_NETWORK_IO_SUSPENDED` | **data:transient** — reset to retry |
| `HTTP 404` on job page | **data:permanent** — archive with reason |
| `No URL available` | **data:permanent** — archive with reason |
| `HTTP 401` / `HTTP 403` on job page | **data:permanent** — archive with reason |
| `ModelHTTPError: 429` | **data:transient** — reset to retry |
| `ModelHTTPError: 401` | **config:auth** — LiteLLM/proxy issue, report only |
| `ModelHTTPError: 400 BadRequestError` | **code:investigate** — bad model input, inspect source |
| `UnexpectedModelBehavior` / `output validation` | **code:investigate** — schema mismatch or prompt issue |
| Scout `HTTPStatusError: 404` on ATS API | **config:ats** — slug stale, disable company |

Errors classed `code:investigate` require reading source files before any fix is proposed.

---

## Phase 3 — Propose Fixes

**Do not apply anything yet.** Build a full fix plan first, then present it.

### For `data:transient` and `data:permanent`

These are straightforward data mutations — no proposal needed, list them in the summary and apply directly.

### For `config:ats`

Read `configs/companies.json`, identify the affected entry, and state what will be changed (`enabled: false`, `status: ats_broken`).

### For `code:investigate`

This is the most important class. For each such error:

1. **Read the relevant source file(s)** — check the agent, the prompt, the output schema, and any pre-processing that touches the input
2. **Understand the root cause** — is it the prompt? The output model? Content truncation? Token limits? An edge case in the input data?
3. **Formulate a concrete fix** — a specific code change (e.g. "truncate `page_text` before passing to agent", "add a fallback in the output schema", "adjust the system prompt constraint")
4. **Show the proposed diff** — present the exact change before touching anything

Format code proposals clearly:

```
### Code Fix: <short title>

**File**: src/enrich/agent.py
**Root cause**: Page text from ti&m careers site exceeds token limit — the
  `_MAX_JD_CHARS = 40_000` cap is applied in the scraper but the Bedrock
  endpoint has a stricter limit for this model.

**Proposed change**:
  Line 8: _MAX_JD_CHARS = 40_000
  →  _MAX_JD_CHARS = 25_000

Apply this fix? (yes / no / modify)
```

Wait for explicit confirmation before writing any code change.

---

## Phase 4 — Apply

After presenting the full plan:

1. Apply all `data:*` fixes to `artifacts/applications.json`
2. Apply all `config:*` fixes to `configs/companies.json`
3. Apply confirmed code fixes to source files
4. Save all modified files

---

## Phase 5 — Report

```
## Pipeline Error Report — <date>

### Scout
  ✓ KNIME — ATS URL broken (404) → disabled in configs/companies.json
  ℹ Salesforce — Auth 401 → check LiteLLM proxy (cannot auto-fix)

### Enrich
  ✓ Reset to retry (transient):   12 jobs
  ✓ Archived (permanent):          3 jobs
  ✓ Code fix applied: reduced _MAX_JD_CHARS to 25_000 (8 jobs affected)
  ℹ Bedrock auth errors:           2 jobs — check .envrc EVALUATE_MODEL config

### Evaluate
  ✓ No errors found

### Next steps
  - Run `make enrich` to retry the 12 + 8 reset jobs
  - Check LiteLLM proxy config for Salesforce / Snap Inc (401 auth)
  - KNIME careers page has moved — run `/app:onboard-company "KNIME"` to rediscover
```

---

## Guardrails

- **Always read source files before proposing a code fix** — never guess at line numbers
- **Never apply a code fix without explicit confirmation** — present the diff, wait for yes/no
- **Never modify files without reading them first**
- **Save `applications.json` and `configs/companies.json` atomically** — full write, not partial
- **Don't change status of jobs already at `archived`, `review`, or `in_progress`**
- **Report everything** — what was fixed, what was skipped, what needs manual intervention
- If the same `code:investigate` error appears across many jobs, fix the code once — not per-job
