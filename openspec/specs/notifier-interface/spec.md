# Specification: Notifier Interface Capability

## Purpose

TBD — defines the abstract `Notifier` interface and `NullNotifier` default implementation that decouple notification logic from pipeline consumers, and specifies how `EvaluateConsumer` and `PipelineRunner` integrate with notifiers.

## Requirements

### Requirement: Notifier abstraction decouples notification logic from pipeline consumers
The system SHALL define a `Notifier` abstract base class in `src/notifications/notifier.py` with three async methods: `on_match(job, score, reasons)`, `on_review(job, score, reasons)`, and `on_run_summary(matched, reviewed)`. A `NullNotifier` concrete subclass SHALL provide no-op implementations of all three methods and serve as the default when notifications are not configured.

#### Scenario: NullNotifier produces no side effects
- **WHEN** `NullNotifier` is used and `on_match`, `on_review`, or `on_run_summary` is called
- **THEN** no network calls are made, no exceptions are raised, and the pipeline continues normally

#### Scenario: Notifier interface is satisfied by any concrete implementation
- **WHEN** a class implements `on_match`, `on_review`, and `on_run_summary` as async methods
- **THEN** it can be passed to `EvaluateConsumer` without modification

### Requirement: EvaluateConsumer accepts a Notifier and calls it at state transitions
`EvaluateConsumer.__init__` SHALL accept an optional `notifier: Notifier` parameter defaulting to `NullNotifier()`. The consumer SHALL call `await self._notifier.on_match(job, score, reasons)` immediately after setting `job["state"] = "match"`, `await self._notifier.on_review(job, score, reasons)` immediately after setting `job["state"] = "review"`, and `await self._notifier.on_run_summary(matched, reviewed)` at the end of `finalize()`.

#### Scenario: Match triggers on_match
- **WHEN** a job scores above `auto_match_threshold` during evaluate
- **THEN** `notifier.on_match` is called with the job dict, final score, and reasons list before `consume()` returns

#### Scenario: Review triggers on_review
- **WHEN** a job scores between `auto_reject_threshold` and `auto_match_threshold`
- **THEN** `notifier.on_review` is called with the job dict, final score, and reasons list before `consume()` returns

#### Scenario: finalize triggers on_run_summary
- **WHEN** `EvaluateConsumer.finalize()` is called after a run
- **THEN** `notifier.on_run_summary` is called with the count of jobs that moved to match and review respectively

#### Scenario: Default notifier requires no caller changes
- **WHEN** `EvaluateConsumer` is constructed without a `notifier` argument
- **THEN** a `NullNotifier` is used and behaviour is identical to before this change

### Requirement: PipelineRunner constructs and injects the correct Notifier
`PipelineRunner` in `src/api/deps.py` SHALL call `AppConfigLoader(self._root).notifications()` and construct a `TelegramNotifier` when both `bot_token` and `chat_id` are present, or a `NullNotifier` otherwise. The notifier SHALL be passed to `EvaluateConsumer` in `evaluate_job`, `evaluate_all`, and `evaluate_next`.

#### Scenario: Configured Telegram produces TelegramNotifier
- **WHEN** `settings.yaml` has `notifications.telegram.bot_token` and `chat_id` set (or env vars present)
- **THEN** `PipelineRunner` passes a `TelegramNotifier` instance to `EvaluateConsumer`

#### Scenario: Unconfigured Telegram produces NullNotifier
- **WHEN** both `bot_token` and `chat_id` are absent or null
- **THEN** `PipelineRunner` passes a `NullNotifier` and no notification attempts are made
