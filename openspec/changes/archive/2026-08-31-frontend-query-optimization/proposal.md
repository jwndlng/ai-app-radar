## Why

Even though backend persistence runs on SQLite, `GET /api/jobs` currently returns all rows including multi-kilobyte text blobs (`description`, `key_responsibilities`, `required_qualifications`, `reasons`) in a single unpaginated JSON payload. Additionally, the Alpine.js frontend computes dashboard state counts by executing 8 sequential `.filter()` scans across all objects in memory on every render cycle, and searches trigger immediate un-debounced string parsing on every keystroke.

Migrating to lightweight summary projections, server-side SQL search/filtering, dedicated `/api/jobs/stats` consumption, and frontend search debouncing will reduce network payload size by ~90% and provide instant, smooth UI interaction.

## What Changes

- Add projection support (`summary` vs `full`) to `DatabaseProvider`, `JobRepository`, and `GET /api/jobs`. In `summary` mode, large text payloads (`description`, `key_responsibilities`, `required_qualifications`, `reasons`, `tech_stack`, `domains`, `sources`) are omitted from list responses.
- Implement `GET /api/jobs/{job_id}` to fetch complete details on demand when a user expands a job card.
- Add server-side filtering and search support to `list_jobs` (`search`, `state`, `status`, `favorited_only`, `sort_by`, `sort_order`, `limit`, `offset`).
- Update `static/index.html` to load dashboard stats from `GET /api/jobs/stats` rather than executing 8 in-memory filter passes on every render.
- Add 300ms debounce to the search input in `static/index.html` to prevent UI thread blocking during typing.

## Capabilities

### New Capabilities
- `job-query-projections`: Lightweight summary vs full detail query projections and server-side search/filtering on job listings.
- `frontend-stats-integration`: Dedicated stats endpoint consumption and debounced search rendering in the web dashboard.

### Modified Capabilities
<!-- None -->

## Impact

- **Storage Layer**: `src/core/storage/base.py`, `src/core/storage/sqlite.py`, `src/core/storage/repository.py`, `src/core/store.py`
- **API Layer**: `src/api/routes.py`
- **Frontend Layer**: `static/index.html`
- **Tests**: `tests/test_storage.py`
