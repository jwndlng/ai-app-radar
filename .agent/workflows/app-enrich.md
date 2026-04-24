---
description: Start the AI Data Analyst enrichment stage
---

# Workflow: /app-enrich

This workflow orchestrates the Stage 2 Enrichment process, where an AI Data Analyst extracts technical metadata from discovered roles.

## Steps

1. **Prerequisites**: Ensure you have latest scouting complete.

// turbo
2. **Run Enrichment Engine**:
   `uv run python -m flows.enrich.main`

3. **Output**: Transition jobs from `new` to `enriched`.
