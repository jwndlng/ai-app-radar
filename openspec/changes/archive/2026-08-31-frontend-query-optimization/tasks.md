## 1. Storage Layer Projections & Filtering

- [x] 1.1 Update `DatabaseProvider` and `SQLiteStorageProvider.list_jobs` to support `projection="summary" | "full"`.
- [x] 1.2 Add server-side query filtering (`search`, `state`, `status`, `favorites_only`, `sort_by`, `sort_order`) in `SQLiteStorageProvider.list_jobs`.
- [x] 1.3 Update `JobRepository` and `ApplicationStore` to expose projection and query filtering parameters.

## 2. API Routes Enhancements

- [x] 2.1 Update `GET /api/jobs` to support `projection="summary"`, `search`, `state`, `status`, `favorites_only`, `sort_by`, `sort_order`, `limit`, and `offset`.
- [x] 2.2 Add `GET /api/jobs/{job_id}` to return the full job record on demand.

## 3. Frontend Optimization in `static/index.html`

- [x] 3.1 Update `loadJobs` to fetch summary records and add `loadJobDetail(id)` for expanding card details.
- [x] 3.2 Implement `loadStats` to populate `stats` via `GET /api/jobs/stats` and remove 8x in-memory `.filter()` calculations from `get stats`.
- [x] 3.3 Add `x-model.debounce.300ms="search"` to search inputs in the UI.

## 4. Verification & Testing

- [x] 4.1 Add unit tests for `projection` filtering and server-side search in `tests/test_storage.py`.
- [x] 4.2 Test single-job detail route `GET /api/jobs/{job_id}`.
- [x] 4.3 Run full automated test suite to ensure zero regressions.
