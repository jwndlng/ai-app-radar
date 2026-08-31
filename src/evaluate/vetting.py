"""Vetter — location pre-filter gate before LLM fit scoring."""

from __future__ import annotations

import unicodedata


class Vetter:
    def __init__(self, profile: dict) -> None:
        loc_prefs = profile.get("location_preferences", {})
        self._accepted = [self._normalize(p) for p in loc_prefs.get("accepted", [])]

    def vet(self, job: dict) -> tuple[bool, str]:
        """Location gate. Returns (passed, reason)."""
        return self._vet_location(job)

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase and strip diacritics so 'Zürich' matches 'zurich'."""
        decomposed = unicodedata.normalize("NFKD", text.lower())
        return "".join(c for c in decomposed if not unicodedata.combining(c))

    def _vet_location(self, job: dict) -> tuple[bool, str]:
        location = self._normalize(job.get("location") or "")
        remote_policy = self._normalize(job.get("remote_policy") or "")
        combined = f"{location} {remote_policy}"

        # Accept if location or remote_policy matches any accepted pattern.
        for pattern in self._accepted:
            if pattern in combined:
                return True, f"Location accepted: matched '{pattern}'"

        # Unknown location but a remote policy is present — pass to the LLM,
        # which receives both fields and can assess geo feasibility.
        if remote_policy:
            return True, f"Remote policy present — LLM will assess geo feasibility"

        return False, f"Location '{job.get('location')} / {job.get('remote_policy')}' not in accepted geo scope"
