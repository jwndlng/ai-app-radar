---
description: Generate the High-Rigor Discovery Dashboard
---

# Workflow: /app-report

This workflow orchestrates the generation of the interactive discovery dashboard.

## Steps

1. **Prerequisites**: Ensure you have latest evaluations complete.
// turbo
2. **Generate Report**: Run the dashboard engine:
   `uv run python -m flows.report.main`

3. **Verification**: Confirm dashboard state.
   `ls -l artifacts/dashboard.html`

4. **Review**: Open the generated report in your local browser:
   `file://{root}/artifacts/dashboard.html`
