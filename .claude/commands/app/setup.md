---
name: "App: Setup"
description: Guided first-time setup — checks tooling, configures LLM keys, generates a profile from your CV, onboards companies, and runs first scout
category: Workflow
tags: [workflow, setup, onboarding]
---

Interactive onboarding wizard. Takes you from a fresh clone to a fully running pipeline in one session. Safe to re-run — detects what is already configured and offers to skip or redo individual steps.

**Invocation**: `/app:setup`

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
  LLM  : ✓ (Gemini direct / Anthropic direct / LiteLLM proxy — describe what you found)
  Profile : ✓ (<name>)
  Companies : <N> tracked

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

Run each check in order. For each failure, print the exact fix command and either offer to run it (if it is safe and automated) or tell the user to run it and come back.

**Check 1 — Python ≥ 3.9**

```bash
python3 --version
```

If the command fails or the version is below 3.9:
```
Python 3.9+ is required.
Install it from https://www.python.org/downloads/ or via your package manager, then re-run /app:setup.
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
Then restart your terminal and re-run /app:setup.
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

If that fails or Chromium is not installed, ask permission to install it (warn: ~150 MB download, 2–3 minutes), then run:
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
     Cost: ~$2/scout (Haiku) to ~$5/scout (Sonnet)

  3) LiteLLM proxy — advanced (self-hosted or team proxy)
```

**Mode 1 — Direct Gemini:**

Prompt for the key:
```
Paste your Google AI Studio key:
```
Validate: must be non-empty. Gemini keys are typically 39-character strings (no specific prefix to validate). If blank, explain and prompt again.

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

Note to user: `claude-haiku-4-5` is chosen as the default to keep costs low (~$0.25/scout). They can change `ADK_MODEL` in `.envrc` to a different Anthropic model any time.

**Mode 3 — LiteLLM proxy:**

Prompt for three values in sequence:
1. `LITELLM_BASE_URL` — the proxy base URL (e.g. `https://litellm.example.com`)
2. `LITELLM_API_KEY` — the proxy key
3. `ADK_MODEL` — the model string to use (e.g. `gemini/gemini-2.5-flash`). Suggest `gemini/gemini-2.5-flash` as default.

Write to `.envrc`:
```
export LITELLM_BASE_URL="<url>"
export LITELLM_API_KEY="<key>"
export ADK_MODEL="<model>"
```

**After writing keys:**

Tell the user to activate the new environment:
```bash
direnv allow
```
If they do not have direnv: `source .envrc`

Then verify the key is readable:
```bash
printenv GEMINI_API_KEY  # or ANTHROPIC_API_KEY / LITELLM_BASE_URL
```

If the output is empty, remind them to run `direnv allow` or `source .envrc` before continuing.

---

### 3. CV-based profile generation

Check `configs/profile.yaml` — if it is non-empty and has an `identity` section, show the current identity name and ask: **Keep existing profile, re-import CV, or skip?** If keeping, skip to step 4.

Ask:
```
Would you like to generate your profile from a CV / resume PDF?
(Recommended — produces a much richer profile than manual entry)

  y) Yes — provide a PDF path
  n) No — I'll answer questions manually
```

**If yes — CV import:**

Ask for the file path:
```
Enter the path to your CV PDF (e.g. ~/Documents/cv.pdf):
```

Read the file using the Read tool. Extract the following fields:

- **Identity**: name, email, phone, location, LinkedIn URL, GitHub URL
- **Headline**: a one-line professional summary (derive from most recent role + specialisation)
- **Intro paragraph**: 2–3 sentences summarising the candidate's background and strengths
- **Exit story**: one sentence describing the candidate's current situation and next step
- **Superpowers**: 3–5 top strengths / technical specialisations
- **Experience**: for each role — company, title, location, period (MM/YYYY–MM/YYYY or PRESENT), bullet highlights, tech stack
- **Education**: institution, degree, field, year
- **Certifications**: name, issuer, year
- **Skills**: flat list

If extraction is incomplete (e.g. no email found), note the missing fields but continue.

Then ask 4–5 targeting questions:

1. **Target roles**: "What job titles are you targeting? (e.g. Senior Security Engineer, Staff Platform Engineer)"
2. **Seniority**: "What level are you targeting? (Senior / Staff / Principal / any)"
3. **Scout keywords**: "List 3–6 keywords for job title filtering (e.g. security, platform, devops). These control which postings the scout picks up."
4. **Mission domains**: "Are there industries or mission areas you prefer or want to avoid? (e.g. prefer: healthcare, climate — avoid: gambling, surveillance)"
5. **Compensation & remote**: "What's your rough compensation range (annual, local currency) and remote preference? (e.g. CHF 160k–200k, hybrid or remote)"

**If no — conversational fallback:**

Ask all the fields above conversationally, one group at a time (identity → narrative → experience → targeting). Use a friendly tone. Fields that are optional can be skipped.

**Generate YAML preview:**

Construct the full `profile.yaml` following the exact schema of the existing file (read `configs/profile.yaml` or the template below):

```yaml
identity:
  name: ...
  email: ...
  phone: ...
  location: ...
  linkedin: ...
  github: ...

targets:
  primary_roles: [...]
  seniority: ...
  archetypes:
    - name: ...
      level: ...
      fit: primary

scout:
  keywords:
    positive: [...]
    negative: [engineer ii, engineer iii, internship, intern, junior, associate]

domains:
  preferred: [...]
  avoid: [...]

compensation:
  range: ...
  currency: ...
  remote: ...

narrative:
  headline: ...
  intro: |
    ...
  exit_story: ...
  superpowers: [...]

experience:
  - company: ...
    role: ...
    location: ...
    period: ...
    highlights: [...]
    tech: [...]

education:
  - institution: ...
    degree: ...
    field: ...
    year: ...

certifications:
  - name: ...
    issuer: ...
    year: ...

skills: [...]
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

For each company the user names, run the full onboard-company flow **inline** (do not call the skill as a subprocess — execute the same steps here):

1. **Discover careers page** — web search for `"<name>" careers jobs site:jobs.ashbyhq.com OR site:boards.greenhouse.io OR site:jobs.lever.co OR site:apply.workable.com OR site:myworkdayjobs.com`, or fetch the company homepage and scan links.

2. **Classify ATS** from the careers URL hostname:

   | Hostname | scan_method | config |
   |---|---|---|
   | `jobs.ashbyhq.com` / `app.ashbyhq.com` | `ashby_api` | slug = first path segment |
   | `boards.greenhouse.io` | `greenhouse_api` | api_base derived from slug |
   | `jobs.lever.co` | `lever_api` | slug = first path segment |
   | `apply.workable.com` | `workable_api` | slug = first path segment |
   | `*.wd*.myworkdayjobs.com` | `workday_api` | tenant + board from URL |
   | anything else | `agent_review` | none |

3. **Verify** the endpoint with a curl check (same as `/app:onboard-company` step 4). If it fails, report and skip this company.

4. **Infer metadata** — brief description and category.

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
- *"Add Python and Kubernetes to my skills"*
- *"I'm now targeting Principal-level roles only"*

Claude Code will read your profile, apply the changes, and write the updated file.

**Fine-tuning in the web UI**

For adjusting skill weights, domain preferences, and evaluation settings, open the dashboard:

```bash
make run
# then open http://localhost:8000
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
