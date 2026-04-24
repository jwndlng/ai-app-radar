---
name: "App: Report"
description: Generate the interactive glassmorphic HTML discovery dashboard
category: Workflow
tags: [workflow, report, pipeline]
---

Generate the interactive discovery dashboard from the current application registries.

**Prerequisites**: Ensure evaluations are complete.

// turbo
**Generate the dashboard:**
```bash
uv run python -m main report
```

**Verify output:**
```bash
ls -l artifacts/dashboard.html
```

**Open in browser** — provide the absolute path for local review:
```
file://{root}/artifacts/dashboard.html
```
