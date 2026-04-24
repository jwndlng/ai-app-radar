# Skill: app_scout

This skill enables the agent to execute and manage the job discovery engine.

## Instructions

### 1. Execution
Use the `/app-scout` slash command to trigger a discovery run.
- **Environment**: Must use the unified root environment (`uv run`).
- **Command**: `uv run python flows/scout/scout.py`

### 2. Configuration
The scout is driven by `configs/scout.yaml`.
- Ensure new companies are added to `tracked_companies` with their appropriate `scan_method`.
- Filters are global and defined in the `title_filter` section.

### 3. Data Integrity
The scout automatically deduplicates against:
- `applications/new.yaml`
- `applications/in_progress.yaml`
- `applications/archived.yaml`
- `flows/scout/history.yaml`

### 4. Debugging
If a scan fails, check the terminal output for "Scraper Error" or "API Error". Verify the company's `careers_url` is still valid and accessible without a VPN.
