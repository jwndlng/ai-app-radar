"""Pipeline state machine — transition graph and undo support."""

from __future__ import annotations

from datetime import datetime

# States whose predecessor is unambiguous (fully determined by the pipeline).
_DETERMINISTIC_PREV: dict[str, str] = {
    "parsed": "discovered",
    "match": "parsed",
    "review": "parsed",
}

# States that can be reached from multiple predecessors.
# These require a `prev_state` field written at transition time.
_AMBIGUOUS_STATES: frozenset[str] = frozenset({"archived", "rejected", "applied"})


class StateMachine:
    @staticmethod
    def touch_updated(job: dict) -> None:
        job["updated_at"] = datetime.now().isoformat()

    @staticmethod
    def prev_state(job: dict) -> str | None:
        """Return the state this job was in before its current state, or None if undoable."""
        state = job.get("state", "")
        if state == "discovered":
            return None
        if state in _DETERMINISTIC_PREV:
            return _DETERMINISTIC_PREV[state]
        if state in _AMBIGUOUS_STATES:
            return job.get("prev_state") or "parsed"
        return None
