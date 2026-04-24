---
name: "App: Onboard Company"
description: Classify a company's careers page ATS, verify it, enrich metadata, and add a configured entry to configs/companies.json
category: Workflow
tags: [workflow, scout, onboarding]
---

Add a new company to the scout. Optionally discovers the careers page if no URL is provided, classifies the ATS, verifies the config is live, infers metadata, and appends a correctly structured entry to `configs/companies.json`.

**Invocation**: `/app:onboard-company "<Company Name>" [careers-url]`

**Input**: The first argument is the company name (required). The second argument is the careers page URL (optional — if omitted, the skill will discover it automatically). If the company name is missing, ask the user before proceeding.

---

## Steps

### 1. Parse inputs

Extract the company name from the arguments. If it is missing, ask the user to supply it before continuing. The careers URL is optional — if not provided, proceed to step 2 (discovery). If provided, skip step 2 and go directly to step 3.

### 2. Discover careers page (skip if URL already provided)

Search for the company's careers page using two methods in order:

**Method A — Web search**: Search for `"<company name>" careers jobs` and examine the results. If any result URL matches a known ATS hostname (`jobs.ashbyhq.com`, `boards.greenhouse.io`, `jobs.lever.co`, `apply.workable.com`) or a careers path on the company's own domain, use that URL.

**Method B — Homepage scrape**: If web search yields no clear match, fetch the company's homepage with Playwright and scan all `<a href>` links. Use the first link whose visible text matches `careers`, `jobs`, `we're hiring`, `open positions`, or `join us` (case-insensitive).

If neither method finds a careers URL: set `status: "needs_manual_review"` on the entry in `configs/companies.json` (if it exists there), report the failure, and stop — do NOT write a new entry.

### 3. Classify the ATS from the URL

Inspect the hostname of the careers URL and determine `scan_method` and slug:

| Hostname | `scan_method` | slug source |
|---|---|---|
| `jobs.ashbyhq.com` | `ashby_api` | first path segment |
| `app.ashbyhq.com` | `ashby_api` | first path segment |
| `boards.greenhouse.io` | `greenhouse_api` | first path segment |
| `jobs.lever.co` | `lever_api` | first path segment |
| `apply.workable.com` | `workable_api` | first path segment |
| `*.wd*.myworkdayjobs.com` | `workday_api` | (none — tenant+board parsed from URL) |
| anything else | `agent_review` | (none) |

The slug is always the first non-empty path segment after stripping trailing slashes (e.g. `https://jobs.ashbyhq.com/acme` → slug `acme`).

For Greenhouse, also derive the API base URL: `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs`.

For Workday, the `careers_url` is used directly — no slug config needed. The provider extracts tenant and board from the URL at runtime. If the URL contains a locale segment like `/en-US/`, use the canonical URL without the locale prefix (e.g. `https://genesys.wd1.myworkdayjobs.com/Genesys`).

If the URL uses a custom domain not in the table above, set `scan_method: agent_review` and note that no structured API provider was detected.

### 4. Verify the entry is live

**For known ATS providers**, make a real API call to verify the slug is valid:

- `ashby_api` — `curl -s -o /dev/null -w "%{http_code}" "https://api.ashbyhq.com/posting-api/job-board/{slug}"`
- `greenhouse_api` — `curl -s -o /dev/null -w "%{http_code}" "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"`
- `lever_api` — `curl -s -o /dev/null -w "%{http_code}" "https://api.lever.co/v0/postings/{slug}?mode=json"`
- `workable_api` — `curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "{}" "https://apply.workable.com/api/v3/accounts/{slug}/jobs"`
- `workday_api` — extract tenant and board from the URL (tenant = first subdomain, board = first non-locale path segment), then: `curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"appliedFacets":{},"limit":1,"offset":0,"searchText":""}' "https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs"`. A 200 with a JSON body confirms the board is valid.

If the response code is not 2xx, **stop**: report the failure, suggest the user double-check the slug or try navigating to the careers URL manually, and do NOT write to `configs/companies.json`.

**For `agent_review`**, verify the URL is reachable:

- `curl -s -o /dev/null -w "%{http_code}" -L "{careers_url}"`

If the response code is not 2xx, **stop**: report that the URL is unreachable and do NOT write.

### 5. Infer metadata

**Description**: Based on the company name and any information gathered so far (careers URL, homepage), write a concise 1-sentence description of what the company does (e.g. `"Builds autonomous mobile robots for industrial logistics."`). Show it and ask the user to confirm, edit, or skip (leave field absent).

**Category**: Based on the company name and careers URL, infer the most appropriate `category` tag (e.g. `"AI/ML"`, `"Fintech"`, `"MedTech"`, `"Robotics"`, `"Cloud"`, `"Enterprise"`, `"CleanTech"`, `"Blockchain"`, `"Social"`). Show the inferred category and ask the user to confirm, override with a different value, or skip (leave field absent).

**Employees**: Ask the user for an approximate headcount band (e.g. `"10-50"`, `"50-200"`, `"200-500"`, `"500+"`). This field is optional — skip if the user leaves it blank.

### 6. Check for duplicates

Read `configs/companies.json`. Scan the `companies` array for any entry whose `name` matches the company name (case-insensitive).

If a match is found, show the existing entry and ask the user: **replace it, or abort?** Proceed only if the user confirms replacement. If replacing, remove the old entry before appending the new one. If aborting, stop here and explain.

### 7. Append the entry to configs/companies.json

Build the entry object:

**For known ATS (e.g. Ashby):**
```json
{
  "name": "<Company Name>",
  "description": "<one-sentence description>",
  "careers_url": "<url>",
  "scan_method": "<method>",
  "scan_method_config": { "slug": "<slug>" },
  "enabled": true,
  "category": "<inferred-or-user-provided>",
  "employees": "<band>"
}
```

**For Greenhouse** (include full API base URL in config):
```json
{
  "name": "<Company Name>",
  "description": "<one-sentence description>",
  "careers_url": "<url>",
  "scan_method": "greenhouse_api",
  "scan_method_config": { "api_base": "https://boards-api.greenhouse.io/v1/boards/<slug>/jobs" },
  "enabled": true
}
```

**For `workday_api`:**
```json
{
  "name": "<Company Name>",
  "description": "<one-sentence description>",
  "careers_url": "https://<tenant>.wd*.myworkdayjobs.com/<board>",
  "scan_method": "workday_api",
  "enabled": true,
  "category": "<inferred-or-user-provided>"
}
```
No `scan_method_config` needed — tenant and board are parsed from `careers_url` at runtime.

**For `agent_review`:**
```json
{
  "name": "<Company Name>",
  "description": "<one-sentence description>",
  "careers_url": "<url>",
  "scan_method": "agent_review",
  "enabled": true
}
```

Omit `scan_method_config` when empty. Omit `description`, `category`, and `employees` if the user skipped them.

Read `configs/companies.json`, append the new entry to the `companies` array, and write the file back.

### 8. Show summary

Print a confirmation:

```
✓ Onboarded: <Company Name>
  ATS detected : <ATS name or "unknown (agent_review)">
  scan_method  : <method>
  slug         : <slug>  (omit if agent_review)
  careers_url  : <url>
  description  : <value or "not set">
  category     : <value or "not set">
  employees    : <value or "not set">
  Entry appended to configs/companies.json
```

If onboarding was aborted at any step, explain what happened and what the user can do next (e.g. check the slug, supply a different URL, or add the entry manually).
