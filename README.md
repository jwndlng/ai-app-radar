# Agentic Application Tracker

> Automated job discovery, enrichment, and fit scoring — with a web dashboard for triage.

> [!WARNING]
> **Early-stage / hobby project.** Expect rough edges, breaking changes, and no support SLA. Use at your own risk.

---

## What it does

Agentic Application Tracker is a self-hosted pipeline that automates the tedious parts of a job search:

1. **Scout** — scans company career pages and ATS APIs for new postings that match your title filters
2. **Enrich** — fetches each listing and uses an LLM to extract structured metadata (location, remote policy, salary, tech stack, responsibilities)
3. **Evaluate** — scores each job against your candidate profile using an LLM, routes to match / review / rejected, and hard-blocks jobs that fail a location gate

Everything is tracked in a local JSON store and surfaced through a web dashboard where you can sort, filter, triage, and track applications.

```
Company career pages & ATS APIs
          │
          ▼  Scout
  Discovers open roles matching your title filters
          │
          ▼  Enrich
  Extracts: location, remote policy, salary, tech stack, domains…
          │
          ▼  Evaluate
  LLM scores fit (0–10) against your profile
  Routes: match → review → rejected → archived
          │
          ▼  Dashboard
  Web UI — sort by last updated, filter by state, triage manually
```

---

## Quick Start

**Requirements:** Python 3.9+, [uv](https://docs.astral.sh/uv/), an Anthropic or Gemini API key

```bash
# 1. Clone and install
git clone https://github.com/your-username/agentic-application-tracker
cd agentic-application-tracker
uv sync

# 2. Install Playwright (for scraping career pages)
uv run playwright install chromium

# 3. Set your LLM API key
export ANTHROPIC_API_KEY=sk-ant-...
# or
export GEMINI_API_KEY=...

# 4. Configure your profile
cp configs/profile.example.yaml configs/profile.yaml
# Edit configs/profile.yaml — add your skills, location preferences, compensation targets

# 5. Configure companies to track
# configs/companies.json is tracked in the repo — edit it to enable/disable companies,
# or add more via the onboard command. Keep personal overrides in companies.local.json (gitignored).

# 6. Start the dashboard
make run
# → http://localhost:8000
```

From the dashboard you can run Scout, Enrich, and Evaluate directly — no CLI needed for day-to-day use.

---

## Configuration

### `configs/profile.yaml`

Defines who you are and what you're looking for. The pipeline scores every job against this file.

Key sections:

| Section | Purpose |
|---|---|
| `targets.primary_roles` | Role titles to target — used in scout title filters |
| `skill_tiers` | `super_power` / `strong` / `low` — LLM uses these to assess tech stack fit |
| `mission_domains` | Domain interest weights (e.g. `cloud_infrastructure: 10`) |
| `location_preferences.accepted` | Accepted locations — used for the location hard-gate in evaluate |
| `compensation` | `minimum` and `target_range` — LLM uses these for compensation scoring |
| `scout_filters` | Keyword allow/block lists for title filtering during scout |

Copy `configs/profile.example.yaml` as a starting point.

### `configs/companies.json`

List of companies to track. Each entry needs a `scan_method` that matches an ATS provider:

| `scan_method` | ATS | Config needed |
|---|---|---|
| `greenhouse_api` | Greenhouse | `api_base` URL |
| `ashby_api` | Ashby | `slug` |
| `lever_api` | Lever | `slug` |
| `workable_api` | Workable | `slug` |
| `workday_api` | Workday | careers URL only |
| `agent_review` | Any (web scrape + LLM) | careers URL only |

`configs/companies.json` is the community-maintained list — it ships with a curated set of companies and grows via PRs. To add a new company interactively, use the onboard command from the dashboard or CLI.

### `configs/settings.yaml`

Pipeline thresholds and model configuration:

```yaml
evaluate:
  auto_reject: 4.0        # score below this → archived
  auto_match: 8.0         # score above this → match
  location_reject_threshold: 2.0  # location score below this → hard rejected
```

---

## Pipeline Stages

### Scout

Discovers new roles from company career pages and ATS APIs. Supported providers:

- **Greenhouse API** — direct job board API
- **Ashby API** — direct job board API
- **Lever API** — direct job board API
- **Workable API** — direct job board API
- **Workday API** — Workday CXS API
- **SmartRecruiters API** — SmartRecruiters API
- **Agent Review** — Playwright headless browser + LLM for any other career page

Jobs are deduplicated by company + title. Duplicate discoveries across sources are merged into a `sources` array on each record.

### Enrich

Fetches each job listing page using a headless browser and passes the text to an LLM for structured extraction. Extracts: title, company, team, location, remote policy, salary range, tech stack, domains, responsibilities, and qualifications.

### Evaluate

Two-phase scoring:

1. **Location pre-filter** — vets the role against `location_preferences` in your profile. Hard-blocks on clearly inaccessible locations.
2. **LLM fit scoring** — scores 0.1–10.0 across four dimensions: overall fit, location, seniority, and compensation. A hard location gate rejects jobs scoring below `location_reject_threshold`.

Routes:
- `score > auto_match` → **match**
- `score < auto_reject` or `location_score ≤ threshold` → **rejected / archived**
- Otherwise → **review**

---

## Directory Layout

```
configs/
  profile.yaml              # Your candidate profile (gitignored — copy from .example)
  profile.example.yaml      # Demo profile for testing
  companies.json            # Community-maintained company list (tracked in git)
  companies.local.json      # Personal enabled/disabled overrides (gitignored)
  settings.yaml             # Pipeline thresholds and model config

src/
  core/                     # Shared: config, store, logger, base agent, state machine
  scout/                    # Discovery: ATS providers, web search, deduplication
  enrich/                   # Metadata extraction from job description pages
  evaluate/                 # Fit scoring: vetter, LLM scorer, consumer
  api/                      # FastAPI routes and pipeline runner
  cli.py                    # CLI entry point

static/
  index.html                # Single-page web dashboard (Alpine.js)

tests/                      # Test suite
tuning/                     # LLM evaluation harness for prompt tuning
openspec/specs/             # Canonical capability specifications

artifacts/                  # Runtime state (gitignored)
  applications.json         # Unified job registry
  logs/                     # Per-run JSONL logs
```

---

## Adding Companies

The fastest way is the onboard command from the dashboard. To add via CLI:

```bash
# Auto-detect ATS and add to companies.json
uv run python -m main onboard "Company Name"

# Or add manually to configs/companies.json — see existing entries for the structure
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: issues and PRs are welcome. This is a hobby project — response time may be slow. Good PR candidates: new ATS providers, bug fixes, documentation improvements.

---

## License

MIT — see [LICENSE](LICENSE).
