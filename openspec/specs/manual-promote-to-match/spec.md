# Spec: Manual Promote to Match

## Purpose

Allow users to manually promote a job from `review` state to `match` state via the API and dashboard UI, and ensure the undo operation correctly reverts such promotions.

## Requirements

### Requirement: User can manually promote a review job to match
The system SHALL allow a job in `review` state to be manually transitioned to `match` state via the existing `/jobs/{job_id}/state` endpoint.

#### Scenario: Promote review job to match
- **WHEN** a POST to `/jobs/{job_id}/state` is made with `{"state": "match"}` and the job exists
- **THEN** the job's state SHALL be set to `match`, `prev_state` SHALL be set to `review`, and `updated_at` SHALL be refreshed

#### Scenario: Reject invalid manual state
- **WHEN** a POST to `/jobs/{job_id}/state` is made with a state not in the allowed set
- **THEN** the endpoint SHALL return HTTP 400

### Requirement: Undo of a manually promoted job returns to review
The state machine SHALL correctly revert a manually promoted `match` job back to `review`.

#### Scenario: Undo manual promotion
- **WHEN** a job was manually promoted from `review` to `match` (prev_state = "review")
- **THEN** undoing the job SHALL set state to `review`

#### Scenario: Undo pipeline-routed match job
- **WHEN** a job was routed to `match` by the evaluate pipeline (no prev_state set)
- **THEN** undoing the job SHALL set state to `parsed`

### Requirement: UI shows promote button on review jobs
The dashboard SHALL display a "Promote to match" action on job cards in `review` state.

#### Scenario: Button visible on review card
- **WHEN** a job card is in `review` state
- **THEN** a "Promote to match" button SHALL be visible alongside the existing reject action

#### Scenario: Button absent on non-review cards
- **WHEN** a job card is in any state other than `review`
- **THEN** no "Promote to match" button SHALL be shown
