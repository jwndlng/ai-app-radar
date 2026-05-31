# Specification: Telegram Notifier Capability

## Purpose

TBD — implements the `Notifier` interface using the Telegram Bot API to deliver per-job match/review alerts and post-run summary messages, with best-effort delivery that never blocks the pipeline.

## Requirements

### Requirement: TelegramNotifier sends a per-job message for matches and reviews
`TelegramNotifier` SHALL implement `Notifier` and send a `sendMessage` request to `https://api.telegram.org/bot{token}/sendMessage` on each `on_match` and `on_review` call. The message SHALL include: job title, company name, final score out of 10, and up to three top reasons. Match messages SHALL be prefixed with `✅ Match`, review messages with `👀 Review`. Notification delivery SHALL be best-effort — any HTTP or network error SHALL be caught, printed to stderr, and silently ignored so the pipeline is never blocked.

#### Scenario: Match message format
- **WHEN** `on_match` is called with a job scoring 8.9 at "Stripe" for "Senior Backend Engineer" with reasons ["remote-friendly", "senior role"]
- **THEN** a Telegram message is sent containing "✅ Match", "Senior Backend Engineer", "Stripe", "8.9/10", and the reasons

#### Scenario: Review message format
- **WHEN** `on_review` is called with a job scoring 7.1
- **THEN** a Telegram message is sent containing "👀 Review" and the score

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
