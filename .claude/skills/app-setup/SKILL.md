# Keep in sync with .gemini/skills/app-setup/SKILL.md

---
name: app-setup
description: Use this skill when the user wants to set up the agentic application tracker for the first time, re-configure LLM keys, regenerate their profile, add companies, or run the first scout.
---

Interactive onboarding wizard. Takes you from a fresh clone to a fully running pipeline in one session. Safe to re-run — detects what is already configured and offers to skip or redo individual steps.

---

## Steps

### 0. Detect existing configuration

Before doing anything else, check the current state:

1. Read `.envrc` — look for any of `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `LITELLM_BASE_URL`. If any are present, note that LLM keys are already configured.
2. Read `configs/profile.yaml` — if the file is non-empty and contains an `identity` section, note that a profile is already configured.
3. Read `configs/companies.json` — count entries in the `companies` array.

If all three are already configured, greet the user with a brief summary of what is set up and offer a menu of individual steps they can re-run:

```
Already configured:
  LLM      : ✓ (Gemini direct / Anthropic direct / LiteLLM proxy — describe what you found)
  Profile  : ✓ (<name>)
  Companies: <N> tracked

What would you like to do?
  1) Re-configure LLM keys
  2) Re-import CV / update profile
  3) Add more companies
  4) Run scout now
  5) Nothing — exit
```

If not fully configured, proceed with the full onboarding flow below.

---

### 1. Prerequisite checks

Run each check in order. For each failure, print the exact fix command and either offer to run it (if safe and automated) or tell the user to run it and come back.

**Check 1 — Python ≥ 3.9**

```bash
python3 --version
```

If the command fails or the version is below 3.9:
```
Python 3.9+ is required.
Install it from https://www.python.org/downloads/ or via your package manager, then re-run setup.
```
Stop.

**Check 2 — uv installed**

```bash
uv --version
```

If the command fails:
```
uv is not installed. Run:
  curl -LsSf https://astral.sh/uv/install.sh | sh
Then restart your terminal and re-run setup.
```
Stop.

**Check 3 — Dependencies installed**

Check whether `.venv` exists:
```bash
ls .venv
```

If absent, ask the user for permission to run `uv sync` (warn: may take 1–2 minutes on first run), then run it:
```bash
uv sync
```

**Check 4 — Playwright Chromium**

```bash
uv run python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.stop()"
```

If that fails, ask permission to install Chromium (warn: ~150 MB download, 2–3 minutes), then run:
```bash
uv run playwright install chromium
```

Once all four checks pass, continue.

---

### 2. LLM key setup

Check `.envrc` for existing LLM keys (see step 0). If keys are already present, show them masked and ask: **Keep existing keys, or re-configure?** If keeping, skip to step 3.

**Ask the user which connection mode they want:**

```
Which LLM provider would you like to use?

  1) Google Gemini — direct (recommended for new users)
     Get a free key at https://aistudio.google.com/app/apikey
     Cost: ~$0 on free tier, ~$0.15/scout on paid

  2) Anthropic Claude — direct
     Get a key at https://console.anthropic.com/settings/keys
     Cost: ~$0.25/scout (Haiku) to ~$5/scout (Sonnet)

  3) LiteLLM proxy — advanced (self-hosted or team proxy)
```

**Mode 1 — Direct Gemini:**

Prompt for the key:
```
Paste your Google AI Studio key:
```
Validate: must be non-empty. If blank, explain and prompt again.

Write to `.envrc`:
```
export GEMINI_API_KEY="<key>"
export ADK_MODEL="gemini/gemini-2.5-flash"
```

**Mode 2 — Direct Anthropic:**

Prompt for the key:
```
Paste your Anthropic API key (starts with sk-ant-):
```
Validate: must start with `sk-ant-`. If it does not, explain and prompt again.

Write to `.envrc`:
```
export ANTHROPIC_API_KEY="<key>"
export ADK_MODEL="anthropic/claude-haiku-4-5"
```

Note to user: `claude-haiku-4-5` is chosen as the default to keep costs low. They can change `ADK_MODEL` in `.envrc` to any other model any time.

**Mode 3 — LiteLLM proxy:**

Prompt for three values in sequence:
1. `LITELLM_BASE_URL` — the proxy base URL (e.g. `https://litellm.example.com`)
2. `LITELLM_API_KEY` — the proxy key
3. `ADK_MODEL` — the model string to use (e.g. `gemini/gemini-2.5-flash`)

Write to `.envrc`:
```
export LITELLM_BASE_URL="<url>"
export LITELLM_API_KEY="<key>"
export ADK_MODEL="<model>"
```

**After writing keys:**

Tell the user to activate the new environment:
```bash
direnv allow    # if using direnv
# or
source .envrc   # without direnv
```

Then verify the key is readable:
```bash
printenv GEMINI_API_KEY  # or ANTHROPIC_API_KEY / LITELLM_BASE_URL
```

If the output is empty, remind them to run `direnv allow` or `source .envrc` before continuing.

---

### 3. Profile setup

Check `configs/profile.yaml` — if it is non-empty and has an `identity` section, show the current identity name and ask: **Keep existing profile, re-import CV, or skip?** If keeping, skip to step 4.

Ask:
```
How would you like to set up your candidate profile?

  1) Use the example profile (Alex Chen) — good for testing the pipeline first
  2) Generate from my CV / resume — recommended for real use
  3) Answer questions manually
```

**Option 1 — Example profile:**

```
This will copy configs/profile.example.yaml to configs/profile.yaml.
Note: this is a fictional profile (Alex Chen, Platform Engineer in Berlin).
The pipeline will run and return real job results, but scoring will reflect
Alex's skills, not yours. You can re-run setup any time to replace it.

Continue with the example profile? (y/n)
```

If yes, copy `configs/profile.example.yaml` to `configs/profile.yaml` and proceed to step 4.

**Option 2 — CV import:**

Ask for the file path or offer to accept pasted text. Read the file using the Read tool. Extract the following fields:

- **Identity**: name, email, location, LinkedIn URL, GitHub URL
- **Narrative**: one-line headline (derive from most recent role + specialisation), one-sentence exit story
- **Experience**: for each role — company, role title, location, period (MM/YYYY–PRESENT), bullet highlights, tech stack
- **Education**: degree, school, period
- **Skills**: languages with proficiency levels, infrastructure/tool list

If extraction is incomplete (e.g. no email found), note the missing fields but continue.

Then ask 4–5 targeting questions:

1. **Target roles**: "What job titles are you targeting? (e.g. Senior Security Engineer, Staff Platform Engineer)"
2. **Scout keywords**: "List 3–6 keywords for job title filtering (these control which postings the scout picks up, e.g. security, platform, devops)"
3. **Location preferences**: "Which locations or remote policies are acceptable? (e.g. Berlin, Remote Europe, EMEA, Global)"
4. **Mission domains**: "Rate your interest 1–10 in any of these (skip ones that don't apply): cloud infrastructure, developer tooling, fintech, AI/ML, healthcare, climate"
5. **Compensation**: "What's your compensation range (annual, local currency)? e.g. EUR 100k minimum, 120–160k target"

**Option 3 — Manual questionnaire:**

Ask all fields conversationally, one group at a time: identity → narrative → experience → targeting. Use a friendly tone. Fields that are optional can be skipped.

**Generate YAML preview (options 2 and 3):**

Construct the full `profile.yaml` using **exactly** this schema (matching `configs/profile.example.yaml` — do not invent field names):

```yaml
identity:
  name: ...
  email: ...
  location: ...
  linkedin: ...
  github: ...

targets:
  primary_roles:
    - ...
  archetypes:
    - name: ...
      level: ...
      fit: primary

narrative:
  headline: ...
  exit_story: ...

experience:
  - company: ...
    role: ...
    location: ...
    period: MM/YYYY -- PRESENT
    highlights:
      - ...
    tech_stack:
      - ...

education:
  - degree: ...
    school: ...
    period: ...

logistics:
  availability: ...
  preferred_locations:
    - ...
  visa_status: ...
  timezone: ...

scout_filters:
  positive:
    - ...
  negative:
    - Sales
    - Marketing
  seniority_boost:
    - Senior
    - Staff
    - Principal
    - Lead

compensation:
  currency: ...
  minimum: ...
  target_range: ...

location_preferences:
  accepted:
    - ...
  remote_eligible: true

mission_domains:
  cloud_infrastructure: 0
  developer_tooling: 0
  distributed_systems: 0
  fintech: 0
  other: 0

skill_tiers:
  super_power:
    - ...
  strong:
    - ...
  low:
    - ...

skills:
  matrix:
    languages:
      - name: ...
        level: 5
    infrastructure:
      - ...
```

Show the full generated YAML in a fenced block. Ask:
```
Does this look correct?
  y) Write to configs/profile.yaml
  e) Edit — tell me what to change and I'll regenerate
  n) Skip for now
```

If the user requests edits, apply them and show the updated YAML for re-confirmation. Repeat until the user confirms or skips.

On confirmation, write the YAML to `configs/profile.yaml`.

---

### 4. Company onboarding

Check `configs/companies.json` — show how many companies are currently tracked.

Ask:
```
Would you like to add companies to track now?
You can add more any time with /app:onboard-company.

Enter a company name (or leave blank to skip):
```

For each company the user names, run the full onboard-company flow **inline**:

1. **Discover careers page** — web search for `"<name>" careers jobs site:jobs.ashbyhq.com OR site:boards.greenhouse.io OR site:jobs.lever.co OR site:apply.workable.com OR site:myworkdayjobs.com`, or fetch the company homepage and scan links.

2. **Classify ATS** from the careers URL hostname:

   | Hostname | scan_method | config |
   |---|---|---|
   | `jobs.ashbyhq.com` / `app.ashbyhq.com` | `ashby_api` | slug = first path segment |
   | `boards.greenhouse.io` | `greenhouse_api` | api_base = `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs` |
   | `jobs.lever.co` | `lever_api` | slug = first path segment |
   | `apply.workable.com` | `workable_api` | slug = first path segment |
   | `*.wd*.myworkdayjobs.com` | `workday_api` | tenant + board from URL |
   | anything else | `agent_review` | none |

3. **Verify** the endpoint with a curl check. If it fails, report and skip this company.

4. **Infer metadata** — brief one-sentence description and category.

5. **Append** to `configs/companies.json`.

After each successful addition, ask:
```
Added ✓. Add another company? (enter name or leave blank to continue):
```

Stop when the user leaves the input blank or says they are done.

---

### 5. First scout

Ask:
```
Setup is complete! Would you like to run the first scout now?
This will check all your tracked companies for matching roles.
(Takes 1–5 minutes depending on company count)

  y) Run now
  n) Skip — I'll run it later with: make scout
```

If yes, run:
```bash
make scout
```

Wait for it to complete, then report: "Scout complete — found N new jobs." (parse the scout output for job count)

---

### 6. Closing message

Print this closing message:

---

**Setup complete!**

**Updating your profile**

You never need to edit `configs/profile.yaml` by hand. Just tell Claude or Gemini:
- *"I joined Acme Corp as a Staff Engineer in January — update my experience"*
- *"Add Rust to my strong skills"*
- *"I'm now targeting Principal-level roles only"*

**Fine-tuning in the web UI**

```bash
make run
# → http://localhost:8000
```

**Key commands**

```bash
make scout       # discover new roles from all tracked companies
make enrich      # extract metadata for discovered jobs
make evaluate    # score jobs against your profile
make sync        # run all three stages in sequence
make run         # start the web dashboard
```

To add a new company any time:
```
/app:onboard-company "Company Name"
```

---
