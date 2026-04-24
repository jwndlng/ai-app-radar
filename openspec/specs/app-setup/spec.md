## Purpose

Guided first-time setup skill (`/app:setup`) that walks a new user through configuring LLM API keys, generating a profile from their CV, onboarding companies, and optionally running the first scout — all in a single conversational flow.

## Requirements

### Requirement: Setup skill entry point
The skill SHALL be invokable as `/app:setup` with no required arguments. On invocation it SHALL detect whether the project is already configured (`.env` with at least one LLM key present and `configs/profile.yaml` non-empty) and branch accordingly: fresh setup for unconfigured projects, or a brief "already configured" confirmation with options to re-run specific steps.

#### Scenario: Fresh project
- **WHEN** `/app:setup` is run and no `.env` or empty `configs/profile.yaml` exists
- **THEN** the skill begins the full onboarding flow from step 1

#### Scenario: Already configured
- **WHEN** `/app:setup` is run and API keys and profile are already present
- **THEN** the skill reports what is configured and offers to re-run individual steps (re-import CV, add companies, run scout)

### Requirement: LLM API key setup
The pipeline routes all LLM calls through LiteLLM (`src/core/agent.py`). Three connection modes are supported depending on the user's environment:

- **Direct Gemini** (recommended for new users): set `GEMINI_API_KEY`; the default model `gemini/gemini-2.5-flash` is already correct, no `ADK_MODEL` needed.
- **Direct Anthropic**: set `ANTHROPIC_API_KEY` (must start `sk-ant-`) and `ADK_MODEL=anthropic/claude-sonnet-4-5`.
- **LiteLLM proxy** (advanced): set `LITELLM_BASE_URL`, `LITELLM_API_KEY`, and optionally `ADK_MODEL`.

The skill SHALL ask which mode the user wants, then prompt for the relevant credentials, validate them, and write the correct variables to `.env`. It SHALL also write `ADK_MODEL` when required by the selected mode.

#### Scenario: Direct Gemini selected
- **WHEN** the user selects Gemini direct and pastes a key
- **THEN** the skill writes `GEMINI_API_KEY=<key>` to `.env` (no `ADK_MODEL` entry needed)

#### Scenario: Direct Anthropic selected
- **WHEN** the user pastes a key beginning with `sk-ant-`
- **THEN** the skill writes `ANTHROPIC_API_KEY=<key>` and `ADK_MODEL=anthropic/claude-sonnet-4-5` to `.env`

#### Scenario: LiteLLM proxy selected
- **WHEN** the user provides a proxy URL and key
- **THEN** the skill writes `LITELLM_BASE_URL=<url>`, `LITELLM_API_KEY=<key>`, and `ADK_MODEL=<model>` to `.env`

#### Scenario: Empty or malformed key
- **WHEN** the user provides a blank or clearly invalid value
- **THEN** the skill explains the expected format and prompts again without writing

### Requirement: CV-based profile generation
The skill SHALL offer to generate `configs/profile.yaml` from a CV/resume PDF. The user SHALL provide a file path. The skill SHALL read the PDF and extract: identity fields (name, email, phone, location, LinkedIn, GitHub), all experience entries (company, role, period, highlights, tech stack), education, certifications, skills, and a narrative headline and intro. It SHALL then ask 4–5 targeted questions to fill the targeting layer (desired roles, seniority, scout filter keywords, mission domain preferences, compensation range, remote preference). It SHALL generate the full profile YAML, show a preview, and write it only after user confirmation.

#### Scenario: Valid CV path provided
- **WHEN** the user provides a path to a readable PDF file
- **THEN** the skill reads it and extracts all available profile fields

#### Scenario: Targeting questions asked
- **WHEN** CV extraction is complete
- **THEN** the skill asks about target roles, seniority level, and key preferences not derivable from the CV

#### Scenario: Preview and confirm
- **WHEN** the full profile YAML is ready
- **THEN** the skill shows it and asks for confirmation or adjustments before writing

#### Scenario: No CV available
- **WHEN** the user skips the CV step
- **THEN** the skill falls back to asking questions conversationally and generates the profile from answers alone

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
