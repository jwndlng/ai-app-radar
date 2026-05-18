## ADDED Requirements

### Requirement: Draft release is created and updated on every push to main
On every push to the `main` branch, the CI system SHALL automatically create or update a GitHub draft release using Release Drafter. The draft SHALL aggregate all merged PRs since the last published release, grouped by label category.

#### Scenario: First push to main after a release
- **WHEN** a commit is pushed to `main` and no draft release exists
- **THEN** a new draft release is created with the next resolved version as the title and aggregated PR changes in the body

#### Scenario: Subsequent push to main
- **WHEN** a commit is pushed to `main` and a draft release already exists
- **THEN** the existing draft release is updated to include any newly merged PRs

### Requirement: Release version is resolved from PR labels
The draft release title and tag SHALL use semantic versioning (`vMAJOR.MINOR.PATCH`) resolved from the labels on merged PRs. The resolver SHALL apply the following precedence: `major` label → bump major, `minor` label → bump minor, `patch` label or no label → bump patch.

#### Scenario: PR labeled minor merged
- **WHEN** a PR with the `minor` label is merged to main
- **THEN** the draft release tag increments the minor version (e.g., v1.0.3 → v1.1.0)

#### Scenario: No bump label on PR
- **WHEN** a merged PR has no major/minor/patch label
- **THEN** the draft release tag increments the patch version by default

### Requirement: Changelog entries are categorized by PR label
The draft release body SHALL group PR entries under human-readable category headings based on their labels. The categories SHALL be: 🚀 Features (`feat`, `feature`, `enhancement`), 🐛 Bug Fixes (`fix`, `bug`, `bugfix`), 🛠 Maintenance (`chore`, `refactor`, `style`, `perf`, `test`, `ci`), 📚 Documentation (`docs`, `doc`, `documentation`).

#### Scenario: Feature PR merged
- **WHEN** a PR with the `feat` label is merged
- **THEN** it appears under the "🚀 Features" section in the draft release body

#### Scenario: PR with no category label merged
- **WHEN** a PR without any category label is merged
- **THEN** it appears in the release body without a category heading (uncategorized)
