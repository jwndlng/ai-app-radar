# Specification: Evaluate Capability

## Purpose
To automatically score discovered job descriptions (from `artifacts/applications.json`) and transition them to prioritized statuses using LLM-based reasoning and the master evaluation rubric.

## Requirements

### Requirement: Mandatory Pre-Filtering
Before full scoring, the evaluate flow SHALL perform a location vetting check:
- **Location Vetting**: Does the role offer Remote (EU/EMEA) or residency in Switzerland (Zurich/Zug/CH)?

Roles failing the location check SHALL be transitioned to `status: archived` with a mandatory
`rejection_reason` explaining the failure.

#### Scenario: Role in blocked location is archived
- **WHEN** `Vetter.vet()` returns `(False, reason)` for a location-blocked role
- **THEN** the job SHALL be set to `status: archived` with `rejection_reason` set to the vetting reason

#### Scenario: Role in accepted location passes to scoring
- **WHEN** `Vetter.vet()` returns `(True, reason)` for a location-accepted role
- **THEN** the job SHALL proceed to LLM fit scoring

### Requirement: LLM Fit Scoring
The evaluate flow SHALL use a single LLM call to assess candidate fit and produce a structured
`FitResult` containing a fit score, role archetype, and reasoning.

The LLM SHALL receive the following inputs:
- Candidate profile summary: `skill_tiers` (super_power / strong / low), `mission_domains`,
  `location_preferences`, and target role summary from `profile.yaml`
- Enriched job data: `tech_stack`, `domains`, `focus_areas`, `key_responsibilities`,
  `required_qualifications`, `location`, `remote_policy`, `salary_range`, `description`

The LLM SHALL score fit on a 0.1–10.0 scale using the following guidance:
- Super-power or strong skill overlap with `tech_stack` is the primary positive signal
- `domains` overlap with high-weight `mission_domains` from the profile is a secondary positive signal
- Remote-eligible or CH/Zurich/Zug location is a positive signal
- `low`-tier skill matches are neutral — not a positive boost
- Seniority mismatch (e.g. junior role title) is a minor negative signal

After the LLM call, `FitScorer` SHALL compute `matched_skills: list[str]` as the
case-insensitive intersection of the job's `tech_stack` with all skills across all profile
`skill_tiers`. The matched skill strings SHALL use the casing from the job's `tech_stack`.

`FitScorer.score()` SHALL return both the `FitResult` and the `matched_skills` list so that
`evaluate.py` can store `matched_skills` on the job record alongside `score`, `archetype`,
and `reasons`.

#### Scenario: High-overlap role scores above 7.0
- **WHEN** the job's `tech_stack` contains multiple super_power or strong skills from the profile
  AND `domains` matches a high-weight mission domain
- **THEN** the LLM SHALL return a score above 7.0

#### Scenario: Domain mismatch role scores below 5.0
- **WHEN** the job's `domains` and `tech_stack` have no meaningful overlap with the candidate profile
- **THEN** the LLM SHALL return a score below 5.0

#### Scenario: Fit scoring failure is logged and job is skipped
- **WHEN** the LLM call raises an exception or returns an invalid result
- **THEN** the job SHALL remain with `status: enriched` and the error SHALL be logged

#### Scenario: matched_skills computed after successful LLM call
- **WHEN** `FitScoringAgent.score()` returns a valid `FitResult`
- **THEN** `FitScorer` SHALL compute `matched_skills` as the case-insensitive intersection of
  `job["tech_stack"]` with all values in `profile_input["skill_tiers"]`

#### Scenario: matched_skills stored on job record
- **WHEN** `FitScorer.score()` returns a result
- **THEN** `evaluate.py` SHALL store `matched_skills` on the job dict alongside `score`,
  `archetype`, and `reasons`

#### Scenario: matched_skills is empty when tech_stack absent
- **WHEN** the job record has no `tech_stack` field or it is an empty list
- **THEN** `matched_skills` SHALL be an empty list and no error SHALL occur

### Requirement: State Transition Logic
Roles SHALL be transitioned in status based on the thresholds in `configs/settings.yaml` (under `evaluate:`, read by `AppConfigLoader` / `EvaluateSettings`):
- **Auto-Reject (score < auto_reject threshold)**: Set `status: archived`.
- **Manual Review (score between thresholds)**: Set `status: review`.
- **Auto-Match (score > auto_match threshold)**: Set `status: in_progress`.

#### Scenario: Low-scoring job is archived
- **WHEN** the LLM fit score is below the `auto_reject` threshold
- **THEN** the job SHALL be set to `status: archived` with `rejection_reason` recording the score

#### Scenario: Mid-range job queued for review
- **WHEN** the LLM fit score is between the `auto_reject` and `auto_match` thresholds
- **THEN** the job SHALL be set to `status: review` and `vetted_at` SHALL be recorded

#### Scenario: High-scoring job moved to in_progress
- **WHEN** the LLM fit score exceeds the `auto_match` threshold
- **THEN** the job SHALL be set to `status: in_progress` and `vetted_at` SHALL be recorded

### Requirement: Evaluate processes jobs concurrently in random order
The evaluate flow SHALL process enriched jobs using N concurrent workers and SHALL randomize item order before processing begins, consistent with the `PipelineRuntime` contract.

#### Scenario: Enriched jobs are shuffled before evaluation starts
- **WHEN** the evaluate flow is invoked and enriched jobs are loaded from the store
- **THEN** the job list SHALL be shuffled in random order so no vendor or batch ordering is preserved across runs

#### Scenario: Multiple jobs scored in parallel
- **WHEN** the evaluate task runs with `concurrency > 1`
- **THEN** up to N LLM fit-scoring calls SHALL execute concurrently, each operating on a different job

#### Scenario: Concurrent workers do not share mutable job state
- **WHEN** two workers run simultaneously
- **THEN** each worker SHALL only mutate its own job dict; no shared mutable state SHALL exist between workers

### Requirement: Evaluate checkpoints state to disk periodically
The `EvaluateConsumer` SHALL implement `checkpoint()` to persist scored results to disk during a long run, so a crash does not lose all completed work.

#### Scenario: Partial results saved after every N completed jobs
- **WHEN** the number of completed evaluations (scored or failed) reaches a multiple of `checkpoint_every`
- **THEN** `EvaluateConsumer.checkpoint()` SHALL call `store.save(all_apps)`, writing the current scored state to `artifacts/applications.json`

#### Scenario: Final save always occurs
- **WHEN** all enriched jobs have been processed
- **THEN** the runtime SHALL call `consumer.finalize()` which SHALL perform a final `store.save(all_apps)` to flush any remaining results

### Requirement: Transient JD Processing
The system SHALL NOT persistently store the full text of the Job Description. The JD SHALL be used during the evaluation phase for analysis and scoring, but MUST be purged from the `applications.json` registry before final persistence.
