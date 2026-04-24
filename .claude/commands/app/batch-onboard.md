---
name: "App: Batch Onboard Companies"
description: Discover careers pages and detect ATS for multiple companies, updating configs/companies.json in bulk
category: Workflow
tags: [workflow, scout, onboarding, batch]
---

Batch-process multiple companies through the same discovery + ATS classification + metadata flow as `/app:onboard-company`. Updates `configs/companies.json` after each entry.

**Invocation**: `/app:batch-onboard [--source <value>] [--batch N] [Company Name 1, Company Name 2, ...]`

**Modes:**
- `--source <value>` — process entries already in `configs/companies.json` with `source == <value>`, `enabled == false`, and no `status` set (e.g. `--source zurich_valley`)
- Name list — process a comma-separated list of company names as new onboarding targets
- Both can be combined (source entries first, then name list)

**Options:**
- `--batch N` — number of entries to process this run (default: 20)

---

## Steps

### 1. Parse arguments

Extract `--source`, `--batch`, and any company names from the arguments.

- If `--source` is provided: load `configs/companies.json` and collect entries where `source == <value>` AND `enabled == false` AND `status` is absent. These are the pending source entries.
- If company names are provided: treat each as a new company to onboard (they may or may not already exist in `configs/companies.json`).
- Apply the `--batch` limit (default 20) to the combined list.

If neither `--source` nor names are provided, ask the user what to process before continuing.

### 2. For each company in the batch

Run the following sub-steps. Write `configs/companies.json` immediately after each company is processed (do not wait until the end of the batch).

#### 2a. Identify starting point
- If this is a source-mode entry: use the existing entry's `name`. The `careers_url` is a placeholder (`{website}/careers`) — treat it as absent and run discovery.
- If this is a name-list entry: check if the company already exists in `configs/companies.json` (case-insensitive name match). If it does, update it. If not, create a new entry.

#### 2b. Discover careers page
Search for the company's real careers page:

**Method A — Web search**: Search `"<company name>" careers jobs`. If any result URL matches a known ATS hostname (`jobs.ashbyhq.com`, `boards.greenhouse.io`, `jobs.lever.co`, `apply.workable.com`) or a careers/jobs path on the company's domain, use that URL.

**Method B — Homepage scrape**: If web search yields no clear match, fetch the company homepage with Playwright and scan all `<a href>` links for text matching `careers`, `jobs`, `we're hiring`, `open positions`, or `join us` (case-insensitive). Use the first match.

If neither method finds a careers URL:
- Set `status: "needs_manual_review"` on the entry, leave `enabled: false`, write to `configs/companies.json`, and move to the next company.

#### 2c. Classify ATS from the resolved URL

| URL pattern | `scan_method` | `scan_method_config` |
|---|---|---|
| `jobs.ashbyhq.com/<slug>` | `ashby_api` | `{"slug": "<slug>"}` |
| `app.ashbyhq.com/<slug>` | `ashby_api` | `{"slug": "<slug>"}` |
| `boards.greenhouse.io/<slug>` | `greenhouse_api` | `{"api_base": "https://boards-api.greenhouse.io/v1/boards/<slug>/jobs"}` |
| `jobs.lever.co/<slug>` | `lever_api` | `{"slug": "<slug>"}` |
| `apply.workable.com/<slug>` | `workable_api` | `{"slug": "<slug>"}` |
| anything else | `agent_review` | (omit) |

If the ATS is an unsupported system (Workday, SmartRecruiters, Taleo, iCIMS, etc.): set `scan_method: "agent_review"` and `status: "ats_unsupported"`.

#### 2d. Infer category and description (lightweight)
Based on the company name and careers URL, infer a `category` tag. Use the existing `category` if already present and non-generic. Only set it if confident — do not prompt the user in batch mode.

Also infer a one-sentence `description` of what the company does (e.g. `"Builds autonomous mobile robots for industrial logistics."`). Use the existing `description` if already present. Only set it if confident — do not prompt the user in batch mode.

#### 2e. Persist result
Update the entry in `configs/companies.json`:
- On success: set `careers_url` to the discovered URL, set `scan_method` and `scan_method_config`, set `enabled: true`, remove `source` field, set `category` and `description` if inferred. Write file.
- On `needs_manual_review` or `ats_unsupported`: set `status`, leave `enabled: false`. Write file.

### 3. Progress report

After the batch completes, print:

```
Batch complete: <N> processed

  ✓ Enabled        : <count>  (careers page found, ATS detected)
  ~ ATS unsupported: <count>  (careers page found, ATS not supported)
  ✗ Manual review  : <count>  (careers page not found)

Remaining <source> entries: <count>
Run /app:batch-onboard --source <value> to continue.
```

If all entries are processed, note that the source queue is empty.
