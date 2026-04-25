# Agentic Application Tracker

> Automated job discovery, enrichment, and fit scoring — with a web dashboard for triage.

The best job opportunities tend to surface when you're already employed and not actively looking — and that's exactly when you're least likely to catch them. I built this tool to keep a continuous eye on the market in the background, so that when a great match appears you get notified instead of missing it entirely.

The project is still mostly manual in its current form, but the long-term plan is to ship a fully containerized version that can run on Kubernetes or any other server — set it up once, let it run. There are plenty of features and rough edges still to tackle, but the core pipeline works. Have fun with it!

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

## Getting Started

**Requirements:** Python 3.9+, [uv](https://docs.astral.sh/uv/), an LLM API key (or Ollama for fully local use)

Choose whichever path fits your setup:

---

### Path A — Claude Code (recommended)

1. Clone the repo and open it in [Claude Code](https://claude.ai/code)
2. Run `/app:setup`

The setup wizard walks you through dependencies, API keys, profile generation from your CV, and adding companies. It detects what is already configured and offers to skip or redo individual steps.

---

### Path B — Gemini CLI

1. Clone the repo and open it in [Gemini CLI](https://geminicli.com)
2. Ask: *"Set up the application tracker for me"*

Gemini will invoke the same setup wizard via its built-in skill.

---

### Path C — Manual

```bash
# 1. Clone and install dependencies
git clone https://github.com/jxnl/agentic-application-tracker
cd agentic-application-tracker
uv sync

# 2. Install Playwright (for scraping career pages, ~150 MB)
uv run playwright install chromium

# 3. Configure your LLM API key
cp .envrc.example .envrc
# Edit .envrc — uncomment and fill in GEMINI_API_KEY or ANTHROPIC_API_KEY
direnv allow   # or: source .envrc

# 4. Configure your profile
cp configs/profile.example.yaml configs/profile.yaml
# Edit configs/profile.yaml — add your skills, location, compensation targets

# 5. Start the dashboard
make run
# → http://localhost:8000
```

From the dashboard you can run Scout, Enrich, and Evaluate directly — no CLI needed for day-to-day use.

---

## Configuration

### LLM provider

All pipeline stages use the model set in `ADK_MODEL` (or per-stage overrides). Every model call goes through LiteLLM, so any LiteLLM-supported provider works — just change the env vars.

**Free options:**

| Option | `ADK_MODEL` value | Key needed | Notes |
|---|---|---|---|
| Google Gemini free tier | `gemini/gemini-2.5-flash` | `GEMINI_API_KEY` | ~1,500 req/day free; best default |
| Groq free tier | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` | Rate-limited but no billing; fast |
| Ollama (local) | `ollama/gemma3:27b` | none | Fully offline; needs ~16 GB RAM |

See `.envrc.example` for all options including Anthropic and LiteLLM proxy.

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
.envrc.example              # Environment variable template (copy to .envrc)

configs/
  profile.yaml              # Your candidate profile (gitignored — copy from .example)
  profile.example.yaml      # Demo profile for testing
  companies.json            # Community-maintained company list (tracked in git)
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

## Running the Application

```bash
make run        # Start the web dashboard → http://localhost:8000
```

From the dashboard you can trigger each pipeline stage manually. Or run them from the CLI:

```bash
make scout      # Discover new roles from all tracked companies
make enrich     # Extract structured metadata for discovered jobs
make evaluate   # Score jobs against your profile
make sync       # Run all three stages in sequence
```

Other useful targets:

```bash
make scout-one COMPANY="Stripe"   # Scout a single company
make enrich-all                   # Enrich all queued jobs (no limit)
make fix-errors                   # Retry jobs that errored in the last run
make help                         # Show all available targets
```

---

## Adding Companies

**With Claude Code or Gemini CLI** (recommended — auto-detects ATS, verifies the endpoint, and appends a validated entry):

```
/app:onboard-company "Company Name"
/app:onboard-company "Company Name" https://jobs.example.com
```

**Manually** — add an entry directly to `configs/companies.json`. See existing entries for the structure or the `configs/companies.json` ATS table in the Configuration section above.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: issues and PRs are welcome. This is a hobby project — response time may be slow. Good PR candidates: new ATS providers, bug fixes, documentation improvements.

---

## License

MIT — see [LICENSE](LICENSE).
