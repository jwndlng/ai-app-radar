---
name: create_report
description: Generate the high-fidelity glassmorphic HTML dashboard for the job discovery pipeline.
---
# create_report

This skill transforms the raw YAML registries into a premium, interactive dashboard for discovery review.

## Instructions

1. **Verification**: Ensure `applications/*.yaml` registries are present and populated.
2. **Generation**: Run the dashboard engine using `python3 -m flows.report.main`.
3. **Verification**: Confirm that `reports/dashboard.html` has been successfully created/updated.
4. **Presentation**: Provide the absolute file path to the user for local browser review.

## Context
- **Root Directory**: Project root.
- **Output**: `reports/dashboard.html`.
