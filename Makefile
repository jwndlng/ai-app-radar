.PHONY: scout enrich evaluate sync fix-errors tune run help

UV := uv run python -m main

# ── Pipeline stages ────────────────────────────────────────────────────────────

scout:          ## Discover new roles
	$(UV) scout

scout-one:      ## Scout a single company: make scout-one COMPANY="Twilio"
	$(UV) scout --company "$(COMPANY)"

enrich:         ## Enrich new jobs (limit 100, 5 workers)
	$(UV) enrich --limit 100 --concurrency 5

enrich-all:     ## Enrich all queued jobs
	$(UV) enrich --concurrency 5

evaluate:       ## Evaluate enriched jobs
	$(UV) evaluate

# ── Web server ─────────────────────────────────────────────────────────────────

run:            ## Start the web server (default: 0.0.0.0:8000)
	PYTHONPATH=src $(UV) serve

# ── Full pipeline ──────────────────────────────────────────────────────────────

sync:           ## Run the full pipeline: scout → enrich → evaluate
	$(UV) sync

fix-errors:     ## Scan last 3 logs per flow for errors, reset retryable jobs
	$(UV) fix-errors

# ── Tuning ─────────────────────────────────────────────────────────────────────

tune:           ## Run scout tuning harness: make tune CASE=google
ifndef CASE
	$(error CASE is required — usage: make tune CASE=google)
endif
	PYTHONPATH=src python -m tuning.runner $(CASE)

# ── Help ───────────────────────────────────────────────────────────────────────

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
