# AI-powered Application Radar

> Automated job discovery, enrichment, and fit scoring — with a web dashboard for triage.

The best job opportunities tend to surface when you're already employed and not actively looking — and that's exactly when you're least likely to catch them. I built this tool to keep a continuous eye on the market in the background, so that when a great match appears you get notified instead of missing it entirely.

The project is still mostly manual in its current form, but the long-term plan is to ship a fully containerized version that can run on Kubernetes or any other server — set it up once, let it run. There are plenty of features and rough edges still to tackle, but the core pipeline works. Have fun with it!

> [!WARNING]
> **Early-stage / hobby project.** Expect rough edges, breaking changes, and no support SLA. Use at your own risk.

---

## Table of Contents

- [How it works](#how-it-works)
- [Getting Started](#getting-started)
  - [Path A — Claude Code](#path-a--claude-code-recommended)
  - [Path B — Gemini CLI](#path-b--gemini-cli)
  - [Path C — Manual](#path-c--manual)
- [Running the Application](#running-the-application)
- [Adding Companies](#adding-companies)
- [LLM Provider Options](#llm-provider-options)
- [Configuration Reference](#configuration-reference)
- [Contributing](#contributing)

---

## How it works

Three pipeline stages run against your list of tracked companies:

1. **Scout** — scans career pages and ATS APIs for new postings matching your title filters
2. **Enrich** — fetches each listing and extracts structured metadata (location, remote policy, salary, tech stack) via LLM
3. **Evaluate** — scores each job 0–10 against your candidate profile and routes it to match / review / rejected

Everything is stored locally and surfaced in a web dashboard for triage.

---

## Getting Started

**Requirements:** Python 3.9+, [uv](https://docs.astral.sh/uv/), an LLM API key (or Ollama for fully local use)

---

### Path A — Claude Code (recommended)

1. Clone the repo and open it in [Claude Code](https://claude.ai/code)
2. Run `/app:setup`

The setup wizard walks you through installing dependencies, configuring your LLM key, generating a profile from your CV, and adding companies to track. It detects what is already configured and offers to skip or redo individual steps.

---

### Path B — Gemini CLI

1. Clone the repo and open it in [Gemini CLI](https://geminicli.com)
2. Ask: *"Set up the application tracker for me"*

Gemini will invoke the same setup wizard via its built-in skill.

---

### Path C — Manual

```bash
# 1. Clone and install
git clone https://github.com/jwndlng/ai-app-radar
cd ai-app-radar
uv sync

# 2. Install Playwright (for scraping career pages, ~150 MB)
uv run playwright install chromium

# 3. Configure your LLM key
cp .envrc.example .envrc
# Edit .envrc — uncomment and fill in your key (see LLM Provider Options below)
direnv allow   # or: source .envrc

# 4. Set up your profile
cp configs/profile.example.yaml configs/profile.yaml
# Edit configs/profile.yaml — add your target roles, skills, location, compensation

# 5. Start the dashboard
make run
# → http://localhost:8000
```

---

## Running the Application

```bash
make run        # Start the web dashboard → http://localhost:8000
```

From the dashboard you can trigger each pipeline stage with a button. Or use the CLI:

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

**With Claude Code or Gemini CLI** (recommended — auto-detects ATS, verifies the endpoint, and writes a validated entry):

```
/app:onboard-company "Company Name"
/app:onboard-company "Company Name" https://jobs.example.com
```

**Manually** — add an entry to `configs/companies.json`. The repo ships with a curated community list. Supported ATS providers:

| `scan_method` | ATS | Config needed |
|---|---|---|
| `greenhouse_api` | Greenhouse | `api_base` URL |
| `ashby_api` | Ashby | `slug` |
| `lever_api` | Lever | `slug` |
| `workable_api` | Workable | `slug` |
| `workday_api` | Workday | careers URL only |
| `agent_review` | Any (web scrape + LLM) | careers URL only |

---

## LLM Provider Options

All pipeline stages use the model set in `ADK_MODEL`. Every call goes through [LiteLLM](https://docs.litellm.ai), so any LiteLLM-supported provider works — just change the env vars in `.envrc`.

**Free options:**

| Option | `ADK_MODEL` | Key | Notes |
|---|---|---|---|
| Google Gemini free tier | `gemini/gemini-2.5-flash` | `GEMINI_API_KEY` | ~1,500 req/day free; best default |
| Groq free tier | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` | Rate-limited, no billing required |
| Ollama (local) | `ollama/gemma3:27b` | none | Fully offline; needs ~16 GB RAM |

See `.envrc.example` for all options including Anthropic and LiteLLM proxy.

---

## Configuration Reference

### `configs/profile.yaml`

Defines who you are and what you're looking for. The pipeline scores every job against this file. Copy `configs/profile.example.yaml` as a starting point.

Key sections:

| Section | Purpose |
|---|---|
| `targets.primary_roles` | Job titles to target — used in scout title filters |
| `skill_tiers` | `super_power` / `strong` / `low` — used to assess tech stack fit |
| `mission_domains` | Domain interest weights (e.g. `cloud_infrastructure: 10`) |
| `location_preferences.accepted` | Accepted locations — used for the location hard-gate |
| `compensation` | `minimum` and `target_range` — used in fit scoring |
| `scout_filters` | Keyword allow/block lists for title filtering |

### `configs/settings.yaml`

Pipeline thresholds:

```yaml
evaluate:
  auto_reject: 4.0        # score below this → archived
  auto_match: 8.0         # score above this → match
  location_reject_threshold: 2.0  # location score below this → hard rejected
```

### Directory layout

```
.envrc.example              # Environment variable template (copy to .envrc)
configs/
  profile.yaml              # Your candidate profile (gitignored)
  profile.example.yaml      # Example profile for testing
  companies.json            # Community-maintained company list
  settings.yaml             # Pipeline thresholds and model config
src/                        # Pipeline source code
static/index.html           # Web dashboard (Alpine.js)
artifacts/                  # Runtime state — job registry and logs (gitignored)
```

---

## Contributing

Issues and PRs are welcome. This is a hobby project — response time may be slow. Good candidates: new ATS providers, bug fixes, documentation improvements.

---

## License

MIT — see [LICENSE](LICENSE).
