# Specification: Telegram Notifier Capability

## Purpose

TBD — implements the `Notifier` interface using the Telegram Bot API to deliver per-job match/review alerts and post-run summary messages, with best-effort delivery that never blocks the pipeline.

## Requirements

### Requirement: TelegramNotifier sends a per-job message for matches and reviews
`TelegramNotifier` SHALL send a `sendMessage` request with `parse_mode: HTML` on each `on_match` and `on_review` call. The message SHALL be formatted as two lines:
1. A bold hyperlink line: `<b><a href="{url}">{title}</a> @ {company}</b>`. If `url` is absent, the title SHALL be rendered as plain bold text without an `<a>` tag.
2. A scores line: `Match — {final}/10  (fit {score} · loc {loc} · sen {sen} · comp {comp})`, using `👀 Review —` prefix for review messages.

Title and company SHALL be HTML-escaped before embedding. The reasons list SHALL NOT be included. Notification delivery SHALL remain best-effort — any HTTP or network error SHALL be caught, printed to stderr, and silently ignored — except an HTTP 429, which SHALL be retried once after honoring Telegram's `retry_after` (capped at 30s) before giving up.

#### Scenario: Match message format with URL
- **WHEN** `on_match` is called with a job with `url="https://example.com/job"`, title `"Senior Backend Engineer"`, company `"Stripe"`, `final_score=8.9`, `score=9.1`, `location_score=8.0`, `seniority_score=9.0`, `compensation_score=8.5`
- **THEN** a Telegram message is sent with `parse_mode: HTML` containing `<b><a href="https://example.com/job">Senior Backend Engineer</a> @ Stripe</b>` on the first line and `Match — 8.9/10  (fit 9.1 · loc 8.0 · sen 9.0 · comp 8.5)` on the second line

#### Scenario: Match message format without URL
- **WHEN** `on_match` is called with a job that has no `url` field
- **THEN** the first line is `<b>Senior Backend Engineer @ Stripe</b>` with no `<a>` tag

#### Scenario: Review message uses review prefix
- **WHEN** `on_review` is called
- **THEN** the scores line is prefixed with `👀 Review —` instead of `✅ Match —`

#### Scenario: HTML special characters are escaped
- **WHEN** `on_match` is called with a job whose title contains `&`, `<`, or `>`
- **THEN** those characters are HTML-escaped in the message so Telegram renders them correctly

#### Scenario: Network failure does not abort the pipeline
- **WHEN** the Telegram API is unreachable during `on_match`
- **THEN** the exception is caught and logged to stderr, and `consume()` continues normally

### Requirement: TelegramNotifier sends a post-run summary message
`TelegramNotifier` SHALL implement `on_run_summary` by sending a single `sendMessage` with the count of matches and reviews from the completed evaluate run, prefixed with `📊 Evaluate complete`. If both counts are zero the summary SHALL still be sent. Errors SHALL be handled identically to per-job messages.

#### Scenario: Summary after a mixed run
- **WHEN** `on_run_summary(matched=3, reviewed=5)` is called
- **THEN** a Telegram message is sent containing "📊 Evaluate complete", "3 matches", "5 reviews"

#### Scenario: Summary after a zero-result run
- **WHEN** `on_run_summary(matched=0, reviewed=0)` is called
- **THEN** a summary message is still sent indicating zero matches and zero reviews

### Requirement: TelegramNotifier respects per-type enable flags from config
`TelegramNotifier` SHALL accept boolean flags `notify_match`, `notify_review`, and `notify_summary` (all defaulting to `True`). When a flag is `False`, the corresponding method SHALL behave as a no-op without making any HTTP call.

#### Scenario: notify_review disabled suppresses review messages
- **WHEN** `TelegramNotifier` is constructed with `notify_review=False`
- **THEN** `on_review` makes no HTTP call and returns immediately

#### Scenario: All flags true sends all message types
- **WHEN** all three flags are `True` (default)
- **THEN** match, review, and summary messages are all sent
