## ADDED Requirements

### Requirement: PR titles must follow conventional commit format
Every pull request targeting `main` SHALL have a title that matches the conventional commit pattern: `<type>[optional scope][optional !]: <description>`. Valid types are: `feat`, `fix`, `chore`, `build`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`. A trailing `!` indicates a breaking change. The check SHALL fail the PR if the title does not match.

#### Scenario: Valid PR title
- **WHEN** a PR is opened or edited with title `feat(ui): add dark mode toggle`
- **THEN** the title check passes

#### Scenario: Invalid PR title
- **WHEN** a PR is opened or edited with title `updated the filter`
- **THEN** the title check fails and the PR cannot be merged until the title is fixed

#### Scenario: Breaking change PR title
- **WHEN** a PR title is `feat!: drop Python 3.10 support`
- **THEN** the title check passes

### Requirement: PRs are automatically labeled by commit type
When a PR is opened, reopened, or edited, the CI system SHALL automatically apply a label matching the conventional commit type from the PR title. This label feeds into Release Drafter's changelog categorization.

#### Scenario: Feature PR auto-labeled
- **WHEN** a PR title starts with `feat:`
- **THEN** the label `feat` is applied to the PR automatically

#### Scenario: Fix PR auto-labeled
- **WHEN** a PR title starts with `fix:`
- **THEN** the label `fix` is applied to the PR automatically
