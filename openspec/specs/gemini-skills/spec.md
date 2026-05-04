# Capability: Gemini CLI Skills

## Purpose

TBD — Gemini CLI skill definitions that mirror the Claude Code app skills, enabling Gemini CLI users to run the same onboarding and company management workflows.

## Requirements

### Requirement: Gemini CLI skill directory exists
The repository SHALL include a `.gemini/skills/` directory containing skill definitions for Gemini CLI users. Each skill SHALL be a subdirectory with a `SKILL.md` file using Gemini CLI frontmatter (`name` and `description` fields).

#### Scenario: Skills directory present after clone
- **WHEN** a user clones the repository and opens it with Gemini CLI
- **THEN** `.gemini/skills/` is present and Gemini CLI discovers the available skills

### Requirement: app-setup Gemini skill
`.gemini/skills/app-setup/SKILL.md` SHALL contain the same setup wizard logic as `.claude/skills/app-setup/SKILL.md`, adapted to Gemini CLI frontmatter format.

#### Scenario: Gemini user triggers setup
- **WHEN** a Gemini CLI user asks to set up the application
- **THEN** Gemini CLI autonomously activates the `app-setup` skill and runs the full setup wizard

#### Scenario: Skill content matches Claude equivalent
- **WHEN** the app-setup logic is updated in `.claude/skills/app-setup/SKILL.md`
- **THEN** `.gemini/skills/app-setup/SKILL.md` SHALL be updated to match (files carry a sync comment)

### Requirement: app-onboard-company Gemini skill
`.gemini/skills/app-onboard-company/SKILL.md` SHALL contain the same onboarding logic as `.claude/skills/app-onboard-company/SKILL.md`, adapted to Gemini CLI frontmatter.

#### Scenario: Gemini user onboards a company
- **WHEN** a Gemini CLI user asks to add a company
- **THEN** Gemini CLI activates the `app-onboard-company` skill and runs the full onboard flow

### Requirement: opsx skills are Claude-only
OpenSpec workflow skills (opsx:*) SHALL NOT be mirrored to `.gemini/skills/`. The artifact-driven workflow is Claude Code-native and depends on Claude Code slash command invocation patterns.

#### Scenario: No opsx skills in Gemini directory
- **WHEN** a user inspects `.gemini/skills/`
- **THEN** no opsx skill directories are present
