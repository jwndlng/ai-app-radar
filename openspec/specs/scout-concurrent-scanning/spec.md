# scout-concurrent-scanning Specification

## Purpose
Defines how the scout orchestrator processes companies concurrently using an async worker queue, and the async HTTP contract for all ATS providers.

## Requirements

### Requirement: Concurrent company scanning via worker queue
The scout orchestrator SHALL process all enabled companies concurrently using a single
`asyncio.Queue` drained by a fixed pool of worker coroutines, replacing the sequential
per-company loop.

#### Scenario: All companies enqueued at start
- **WHEN** `run()` is called
- **THEN** all enabled companies SHALL be enqueued before any worker begins processing

#### Scenario: Workers drain queue concurrently
- **WHEN** the queue is populated
- **THEN** worker coroutines SHALL pull and process companies concurrently until the
  queue is empty

#### Scenario: Ingestion runs after all workers finish
- **WHEN** all workers have completed and the queue is drained
- **THEN** `_ingest()` SHALL be called exactly once to persist results

### Requirement: ATS providers use async HTTP
All ATS provider `scout` methods (Greenhouse, Ashby, Lever, Workable, SmartRecruiters,
HTTP) SHALL use `httpx.AsyncClient` and be declared `async def`, so they do not block the
event loop during concurrent execution.

#### Scenario: Concurrent ATS calls do not block each other
- **WHEN** multiple workers are processing ATS companies simultaneously
- **THEN** each provider's HTTP call SHALL yield to the event loop while waiting for the
  response, allowing other workers to make progress

### Requirement: Pagination politeness pause
When `WebsearchProvider` follows a `next_page_url` to fetch additional pages for the same
company, it SHALL pause briefly between page requests to avoid rapid consecutive requests
to the same server.

#### Scenario: Pause between paginated pages
- **WHEN** the agent returns a `next_page_url` and the provider fetches the next page
- **THEN** a short sleep of ≤ 0.25s SHALL occur before the next page request

#### Scenario: No pause on first page
- **WHEN** the provider fetches the first page for a company
- **THEN** no sleep SHALL occur before that request
