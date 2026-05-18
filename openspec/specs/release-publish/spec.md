## ADDED Requirements

### Requirement: Docker image provenance is attested on release publish
When a GitHub release is published, the CI system SHALL generate a build provenance attestation for the Docker image that was pushed to GHCR and attach it to the registry entry.

#### Scenario: Release published with a version tag
- **WHEN** a GitHub release is published with a `v*` tag
- **THEN** a build provenance attestation is created for the Docker image at `ghcr.io/<owner>/ai-app-radar:<tag>` and pushed to the registry

### Requirement: Docker pull instructions are appended to release notes
When a GitHub release is published, the CI system SHALL append Docker pull instructions for both the versioned tag and `latest` to the release body.

#### Scenario: Release notes updated after publish
- **WHEN** a release is published
- **THEN** the release body is updated to include a "Docker Image" section with `docker pull` commands for the versioned tag and `latest`

#### Scenario: Existing release notes preserved
- **WHEN** the CI appends Docker instructions
- **THEN** the original release body content written by the author is preserved above the appended section
