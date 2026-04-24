# agent-review-provider Specification

## Purpose
Defines the `WebsearchProvider` behaviour for `agent_review` companies: Playwright-based page fetching, LLM-driven job extraction, and title filtering.

## Requirements

### Requirement: Playwright page fetch
The `agent_review` provider SHALL use Playwright to load the `careers_url` in a headless browser and return the full rendered content. Only the `body` inner text SHALL be passed to the LLM to avoid overwhelming the context window with `<head>` markup.

#### Scenario: Page loads successfully
- **WHEN** Playwright navigates to `careers_url` and the page renders
- **THEN** the provider extracts the inner text of the `body` element and proceeds to the extraction step

#### Scenario: Page fails to load
- **WHEN** Playwright raises a timeout or navigation error
- **THEN** the provider logs the error and returns an empty list (no crash, no retry)

### Requirement: Structured LLM job extraction
The provider SHALL pass the body content to the scout agent with a prompt that instructs the model to return a structured list of open roles. The prompt SHALL request exactly the fields defined by the output model and instruct the model to return only roles that are currently open (not closed, expired, or "coming soon").

#### Scenario: LLM returns valid job list
- **WHEN** the agent returns a parsed job list
- **THEN** each item is mapped to `{title, url, company, location}` and passed to the caller

#### Scenario: LLM returns empty list
- **WHEN** the model finds no matching open roles on the page
- **THEN** the provider returns an empty list without error

### Requirement: Optional content_selector narrows extraction scope
Each `agent_review` company config MAY include a `content_selector` CSS selector. When present, the provider SHALL use `page.locator(content_selector).inner_text()` to extract only the matching subtree. When absent or when the selector matches no element, the provider SHALL fall back to `page.locator("body").inner_text()`.

#### Scenario: content_selector matches an element
- **WHEN** the company config has `content_selector: "main#jobs"` and the page contains that element
- **THEN** only the text content of that element is passed to the LLM

#### Scenario: content_selector matches nothing
- **WHEN** the company config has `content_selector` set but the selector finds no element on the page
- **THEN** the provider falls back to the full body text and logs a warning

#### Scenario: content_selector absent
- **WHEN** the company config has no `content_selector` field
- **THEN** the provider uses `body` as the default extraction target

### Requirement: Title filtering applied after extraction
Extracted jobs SHALL be passed through the existing `filter_job(title, filters)` method from `BaseProvider` before being returned, consistent with all other providers.

#### Scenario: Extracted title matches positive filter
- **WHEN** a job title matches the configured positive keywords and no negative keywords
- **THEN** it is included in the returned list

#### Scenario: Extracted title matches negative filter
- **WHEN** a job title matches a negative keyword
- **THEN** it is excluded from the returned list
