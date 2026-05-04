## Purpose

Guided first-time setup skill (`/app:setup`) that walks a new user through configuring LLM API keys, generating a profile from their CV, onboarding companies, and optionally running the first scout — all in a single conversational flow.

## Requirements

### Requirement: Setup skill entry point
The skill SHALL be invokable as `/app:setup` (Claude Code) or by asking the Gemini CLI to "set up the application". On invocation it SHALL detect whether the project is already configured (`.envrc` with at least one LLM key present and `configs/profile.yaml` non-empty) and branch accordingly: fresh setup for unconfigured projects, or a brief "already configured" confirmation with options to re-run specific steps.

#### Scenario: Fresh project
- **WHEN** `/app:setup` is run and no `.envrc` exists or `configs/profile.yaml` is absent
- **THEN** the skill begins the full onboarding flow from step 1

#### Scenario: Already configured
- **WHEN** `/app:setup` is run and API keys and profile are already present
- **THEN** the skill reports what is configured and offers to re-run individual steps (re-import CV, add companies, run scout)

### Requirement: LLM API key setup
The pipeline routes all LLM calls through LiteLLM (`src/core/agent.py`). Three connection modes are supported:

- **Direct Gemini** (recommended for new users): set `GEMINI_API_KEY`; default model `gemini/gemini-2.5-flash` requires no `ADK_MODEL` entry.
- **Direct Anthropic**: set `ANTHROPIC_API_KEY` (must start `sk-ant-`) and `ADK_MODEL=anthropic/claude-sonnet-4-6`.
- **LiteLLM proxy** (advanced): set `LITELLM_BASE_URL`, `LITELLM_API_KEY`, and optionally `ADK_MODEL`.

The skill SHALL ask which mode the user wants, prompt for relevant credentials, validate them, and write the correct variables to `.envrc`. It SHALL also write `ADK_MODEL` when required by the selected mode. After writing, the skill SHALL instruct the user to run `direnv allow` or `source .envrc`.

#### Scenario: Direct Gemini selected
- **WHEN** the user selects Gemini direct and pastes a key
- **THEN** the skill writes `export GEMINI_API_KEY="<key>"` to `.envrc`

#### Scenario: Direct Anthropic selected
- **WHEN** the user pastes a key beginning with `sk-ant-`
- **THEN** the skill writes `export ANTHROPIC_API_KEY="<key>"` and `export ADK_MODEL="anthropic/claude-sonnet-4-6"` to `.envrc`

#### Scenario: LiteLLM proxy selected
- **WHEN** the user provides a proxy URL and key
- **THEN** the skill writes `export LITELLM_BASE_URL="<url>"`, `export LITELLM_API_KEY="<key>"`, and `export ADK_MODEL="<model>"` to `.envrc`

#### Scenario: Empty or malformed key
- **WHEN** the user provides a blank or clearly invalid value
- **THEN** the skill explains the expected format and prompts again without writing

### Requirement: CV-based profile generation
The skill SHALL generate `configs/profile.yaml` using the exact field schema of `configs/profile.example.yaml`. Required top-level keys are: `identity`, `targets`, `narrative`, `experience`, `education`, `logistics`, `scout_filters`, `compensation`, `location_preferences`, `mission_domains`, `skill_tiers`, `skills`. The skill SHALL NOT generate fields with names that differ from this schema (e.g. `scout.keywords` is wrong; `scout_filters` is correct).

#### Scenario: Valid CV path provided
- **WHEN** the user provides a path to a readable PDF or text file
- **THEN** the skill reads it and extracts identity, experience, education, skills, and narrative fields

#### Scenario: Targeting questions asked
- **WHEN** CV extraction is complete or the user skips the CV step
- **THEN** the skill asks about target roles, seniority level, scout filter keywords, location preferences, compensation range, and remote preference

#### Scenario: Preview and confirm
- **WHEN** the full profile YAML is ready
- **THEN** the skill shows the complete YAML and asks for confirmation or adjustments before writing to `configs/profile.yaml`

#### Scenario: No CV available
- **WHEN** the user skips the CV step
- **THEN** the skill collects all fields conversationally and generates the profile from answers alone

#### Scenario: Generated profile is valid
- **WHEN** the profile is written
- **THEN** all top-level keys match `configs/profile.example.yaml` exactly and the pipeline can load it without error

### Requirement: Initial company onboarding
The skill SHALL prompt the user to name companies they want to track. For each company it SHALL apply the same classification and verification logic as `/app:onboard-company` — detect ATS, verify the endpoint is live, and append to `configs/companies.json`. The user SHALL be able to add multiple companies in one session and stop at any time.

#### Scenario: Company added successfully
- **WHEN** the user names a company and it is verified
- **THEN** it is appended to `configs/companies.json` and confirmed

#### Scenario: User stops adding companies
- **WHEN** the user says they are done or leaves the input blank
- **THEN** the skill moves to the next step without requiring any minimum number of companies

### Requirement: First scout offer
After completing setup the skill SHALL offer to run the first scout immediately. If accepted it SHALL run `make scout` (or equivalent) and report the summary result.

#### Scenario: User accepts first scout
- **WHEN** the user agrees to run the first scout
- **THEN** the skill executes the scout and summarises how many jobs were found

#### Scenario: User declines
- **WHEN** the user declines
- **THEN** the skill skips and moves to the closing message

### Requirement: Closing guidance
The skill SHALL end with a concise message explaining the two ways to manage the profile going forward: (1) ask Claude or Gemini at any time to update skills, experience, or targeting by describing the change in plain language, and (2) use the web UI (`make run` → localhost:8000) for fine-grained editing of skill tiers, domain weights, and preferences. It SHALL also print the key commands to run the pipeline manually.

#### Scenario: Closing message shown
- **WHEN** setup completes (whether or not scout was run)
- **THEN** the skill prints the guidance about Claude/Gemini updates, the web UI, and the main pipeline commands
