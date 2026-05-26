## Purpose

Documents the requirements for the README "Optimization Tips" section — its placement, content, formatting, and cross-references — so that users can tune pipeline cost and quality after initial setup.

## Requirements

### Requirement: Optimization Tips section exists in README
README.md SHALL contain a dedicated "Optimization Tips" section placed after "Running the Application" and before "Adding Companies", with a matching entry in the Table of Contents.

#### Scenario: Section is present and in the correct position
- **WHEN** a reader opens README.md
- **THEN** the "Optimization Tips" heading appears after the "Running the Application" section and before the "Adding Companies" section

#### Scenario: Section is linked from the Table of Contents
- **WHEN** a reader views the Table of Contents
- **THEN** an "Optimization Tips" entry is present and links to the section anchor

### Requirement: agent_review company limit tip
The Optimization Tips section SHALL document that each `agent_review` company triggers a full browser scrape and LLM parse on every pipeline run, and SHALL recommend keeping the number of `agent_review` entries to 5 or fewer.

#### Scenario: Tip is present with a concrete limit
- **WHEN** a reader views the Optimization Tips section
- **THEN** the tip for `agent_review` states a numeric upper bound (≤ 5) and explains the per-company cost

### Requirement: Scout filter specificity tip
The Optimization Tips section SHALL advise users to define specific `title_include` substrings rather than broad terms, and SHALL explain that loose filters pull in irrelevant jobs that consume enrich and evaluate LLM budget.

#### Scenario: Tip explains downstream cost of loose filters
- **WHEN** a reader views the Optimization Tips section
- **THEN** the scout filter tip mentions that irrelevant jobs waste downstream LLM calls (enrich + evaluate)

### Requirement: LLM cost control tip
The Optimization Tips section SHALL recommend using a free-tier model (e.g. `gemini/gemini-2.5-flash`) for enrich and evaluate stages, and SHALL note that stronger models should be reserved for `agent_review` or interactive use.

#### Scenario: Tip names a concrete free-tier example
- **WHEN** a reader views the Optimization Tips section
- **THEN** the LLM cost tip references at least one specific free-tier model as an example

### Requirement: Evaluate threshold tuning tip
The Optimization Tips section SHALL advise users to keep the default `auto_reject` and `auto_match` thresholds for the first run and adjust them only after reviewing initial results.

#### Scenario: Tip defers threshold changes to after first run
- **WHEN** a reader views the Optimization Tips section
- **THEN** the threshold tip instructs users to run the pipeline at least once before lowering `auto_reject` or raising `auto_match`

### Requirement: agent_review callout in Adding Companies table
The `agent_review` row in the Adding Companies scan-method table SHALL include a parenthetical note directing users to the Optimization Tips section.

#### Scenario: Callout is present on the agent_review row
- **WHEN** a reader views the Adding Companies section
- **THEN** the `agent_review` row contains a link or reference to the Optimization Tips section

### Requirement: Tips use GitHub-flavored callout format inside a collapsible block
Each tip in the Optimization Tips section SHALL use a `> [!TIP]` GitHub-flavored callout block, and all tips SHALL be wrapped in a `<details>` / `<summary>` element so the section is collapsed by default.

#### Scenario: Section renders as collapsed by default
- **WHEN** a reader views README.md on GitHub
- **THEN** the Optimization Tips content is hidden behind a collapsed `<details>` block

#### Scenario: Individual tips use the TIP callout style
- **WHEN** the `<details>` block is expanded
- **THEN** each tip is rendered as a `> [!TIP]` admonition block
