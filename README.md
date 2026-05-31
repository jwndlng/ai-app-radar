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
- [Optimization Tips](#optimization-tips)
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

**Requirements:** Python 3.9+, [uv](https://docs.astral.sh/uv/), any LLM API key — [Google Gemini](https://aistudio.google.com/app/apikey), [Anthropic](https://console.anthropic.com/settings/keys), or anything supported by [LiteLLM](https://docs.litellm.ai/docs/providers) (Groq, Bedrock, Azure, …) — or [Ollama](https://ollama.com) for fully local use. Plus either [direnv](https://direnv.net) or `source .envrc` in each terminal session.

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

The dashboard is the recommended way to use the app — Scout, Enrich, and Evaluate are all triggerable with a button, results update in real time, and running tasks can be cancelled at any time via the × button on the task card. The layout is responsive and works on mobile.

<details>
<summary>CLI usage (advanced — no UI required)</summary>

```bash
make scout      # Discover new roles from all tracked companies
make enrich     # Extract structured metadata for discovered jobs
make evaluate   # Score jobs against your profile
make sync       # Run all three stages in sequence

make scout-one COMPANY="Stripe"   # Scout a single company
make enrich-all                   # Enrich all queued jobs (no limit)
make fix-errors                   # Retry jobs that errored in the last run
make help                         # Show all available targets
```

</details>

---

## Optimization Tips

<details>
<summary>Show optimization tips</summary>

> [!TIP]
> **Limit `agent_review` companies**
> Each `agent_review` entry triggers a full Playwright browser scrape plus an LLM parse on every pipeline run. Costs and run times scale linearly — keep it to **5 or fewer** `agent_review` companies. Use API-based providers (`greenhouse_api`, `ashby_api`, `lever_api`, etc.) wherever possible; they are fast, free, and don't consume LLM budget.

> [!TIP]
> **Keep scout filters specific**
> Broad `title_include` patterns (e.g. `"engineer"`) pull in large volumes of irrelevant jobs. Every job that passes the scout filter gets sent to enrich and evaluate — both of which make LLM calls. Use precise title substrings (e.g. `"Staff Software Engineer"`, `"Senior Backend Engineer"`) to keep the job set small and the results relevant.

> [!TIP]
> **Use a free-tier model for enrich and evaluate**
> The enrich and evaluate stages run on every job in the queue. A fast free-tier model such as `gemini/gemini-2.5-flash` (~1,500 req/day free) is more than sufficient for structured extraction and fit scoring. Reserve stronger or paid models for `agent_review` scraping or interactive use.

> [!TIP]
> **Tune evaluate thresholds after the first real run**
> The default thresholds (`auto_reject: 4.0`, `auto_match: 8.0`) are conservative by design. Run the pipeline once at defaults and review the results before adjusting — lowering `auto_reject` floods the review queue; raising `auto_match` hides borderline matches. Calibrate against real output, not guesses.

</details>

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
| `agent_review` | Any (web scrape + LLM) | careers URL only (see [Optimization Tips](#optimization-tips)) |

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

Pipeline thresholds and notification settings:

```yaml
evaluate:
  auto_reject: 4.0        # score below this → archived
  auto_match: 8.0         # score above this → match
  location_reject_threshold: 2.0  # location score below this → hard rejected

notifications:
  telegram:
    bot_token: null       # or set TELEGRAM_BOT_TOKEN env var
    chat_id: null         # or set TELEGRAM_CHAT_ID env var
    notify_match: true    # per-job message on match
    notify_review: true   # per-job message on review
    notify_summary: true  # post-evaluate summary
    notify_scout: true    # post-scout summary
    notify_enrich: true   # post-enrich summary
```

**Telegram setup:** create a bot via [@BotFather](https://t.me/BotFather), get your `chat_id` from [@userinfobot](https://t.me/userinfobot), then add both to `.envrc` or `settings.yaml`. Credentials in `settings.yaml` take precedence over environment variables. Send `/start` to your bot at least once before the first run.

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
