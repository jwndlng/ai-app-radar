---
description: Run the high-rigor evaluation and scoring pipeline
---

## Steps

1. **Strategic Scoring**: Analyze alignment against Jan's profile.

// turbo
2. **Run Evaluation Engine**:
   `uv run python -m flows.evaluate.main`

3. **Output**: Transition jobs from `enriched` to `review` or `archived`.
