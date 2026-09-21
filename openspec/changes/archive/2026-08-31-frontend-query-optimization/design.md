## Context

With SQLite storage now powering the backend, all application records are stored in `artifacts/radar.db`. However, the API endpoint `GET /api/jobs` currently returns all rows including unneeded, heavy JSON text payloads (`description`, `key_responsibilities`, `required_qualifications`, `reasons`, `tech_stack`, `domains`, `sources`).

In the frontend (`static/index.html`), Alpine.js manages all jobs in client memory, computing state counts via 8 sequential `.filter()` scans and recalculating filtered/sorted subsets on every keystroke.

## Goals / Non-Goals

**Goals:**
- **Summary vs Detail Projections:** Split list queries (`summary` projection containing only card-level metadata) from single-item queries (`full` projection with deep descriptions and evaluation reasons).
- **On-Demand Detail Fetching:** Provide `GET /api/jobs/{job_id}` to load full job details when the user clicks to expand a card in the dashboard.
- **Server-Side Filtering & Sorting:** Support `state`, `status`, `search`, `favorites_only`, `sort_by`, and `sort_order` directly in the database provider.
- **Direct Stats Endpoint Consumption:** Replace the 8-pass client-side filter computation with direct `GET /api/jobs/stats` fetching.
- **Debounced UI Search:** Add 300ms debounce to the search input to keep the UI smooth and responsive.

**Non-Goals:**
- Removing client-side pagination / infinite scroll UI (existing 50-item view remains clean while backed by server-filtered data).

## Decisions

### 1. Database Query Projection Parameter (`projection="summary" | "full"`)
- **Decision:** Add a `projection` parameter to `DatabaseProvider.list_jobs()`.
- **Implementation:**
  - `summary`: Skips deserializing the heavy `data` JSON column, returning only relational metadata (`id`, `hash_id`, `company`, `title`, `url`, `location`, `state`, `status`, `final_score`, `location_score`, `seniority_score`, `favorited`, `discovered_at`, `updated_at`, `vetted_at`, `archived_at`, `error_message`).
  - `full`: Merges row columns with `data` JSON (used for single-job inspection or pipeline consumers that need full context).
- **Rationale:** Reduces network response payloads by over 90% (from megabytes to tens of kilobytes).

### 2. Single-Job Detail Endpoint (`GET /api/jobs/{job_id}`)
- **Decision:** Implement `GET /api/jobs/{job_id}` in `src/api/routes.py`.
- **Rationale:** When a user expands a job card in the dashboard, the frontend fetches the full record and caches it in the card state.

### 3. Server-Side SQL Filtering & Sorting
- **Decision:** Enhance `SQLiteStorageProvider.list_jobs` with parameterized SQL clauses:
  - `search`: `(title LIKE ? OR company LIKE ? OR location LIKE ?)`
  - `favorited_only`: `favorited = 1`
  - `sort_by` / `sort_order`: dynamic ORDER BY with sanitized column names (`updated_at`, `final_score`, `title`, `company`).

### 4. Direct `/api/jobs/stats` Consumption in Frontend
- **Decision:** In `static/index.html`, replace the computed `stats` property with an explicit `stats` state object populated via `fetch('/api/jobs/stats')`.
- **Rationale:** Eliminates repeated 8x `.filter()` loops across thousands of items in the browser's JavaScript engine.

## Risks / Trade-offs

- **[Risk] Expand card network latency** → **Mitigation:** Instant expand with fallback loading skeleton while `GET /api/jobs/{id}` resolves, with in-memory caching of already expanded jobs.
- **[Risk] Search performance on large datasets** → **Mitigation:** Substring `LIKE` queries on indexed SQLite columns evaluate in <10ms for thousands of rows.
