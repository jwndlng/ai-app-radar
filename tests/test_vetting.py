from __future__ import annotations

import pytest

from evaluate.vetting import Vetter


@pytest.fixture
def vetter() -> Vetter:
    profile = {
        "location_preferences": {
            "accepted": ["zurich", "switzerland", "remote emea", "remote europe"]
        }
    }
    return Vetter(profile)


def test_vet_logistics_ch_location(vetter: Vetter) -> None:
    passed, reason = vetter.vet({"location": "Zurich, Switzerland"})
    assert passed is True
    assert "zurich" in reason.lower() or "switzerland" in reason.lower()


def test_vet_logistics_remote_emea(vetter: Vetter) -> None:
    passed, reason = vetter.vet({"location": "Remote EMEA"})
    assert passed is True
    assert "remote emea" in reason.lower()


def test_vet_logistics_blocked_us(vetter: Vetter) -> None:
    passed, reason = vetter.vet({"location": "Remote US"})
    assert passed is False
    assert "not in accepted geo scope" in reason.lower()


def test_vet_logistics_unknown_location(vetter: Vetter) -> None:
    passed, reason = vetter.vet({"location": "London, UK"})
    assert passed is False
    assert "not in accepted geo scope" in reason.lower()


def test_vet_logistics_remote_policy_fallback(vetter: Vetter) -> None:
    """Location field absent but remote_policy is present — should pass to LLM."""
    passed, reason = vetter.vet({"location": "", "remote_policy": "Remote"})
    assert passed is True
    assert "remote policy present" in reason.lower()


def test_vet_full_pipeline_pass(vetter: Vetter) -> None:
    job = {"title": "Python Security Architect", "location": "Remote EMEA"}
    passed, reason = vetter.vet(job)
    assert passed is True


def test_vet_full_pipeline_blocked_location(vetter: Vetter) -> None:
    job = {"title": "Senior Security Engineer", "location": "Remote US"}
    passed, reason = vetter.vet(job)
    assert passed is False
