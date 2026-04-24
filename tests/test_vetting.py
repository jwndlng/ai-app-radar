from __future__ import annotations

import pytest

from evaluate.vetting import Vetter


@pytest.fixture
def vetter() -> Vetter:
    profile = {"specialization": ["Python", "Infrastructure-as-Code", "Security Engineering"]}
    return Vetter(profile)


def test_vet_logistics_ch_location(vetter: Vetter) -> None:
    passed, reason = vetter.vet_logistics({"location": "Zurich, Switzerland"})
    assert passed is True
    assert "zurich" in reason.lower()


def test_vet_logistics_remote_emea(vetter: Vetter) -> None:
    passed, reason = vetter.vet_logistics({"location": "Remote EMEA"})
    assert passed is True
    assert "emea" in reason.lower()


def test_vet_logistics_blocked_us(vetter: Vetter) -> None:
    passed, reason = vetter.vet_logistics({"location": "Remote US"})
    assert passed is False
    assert "remote us" in reason.lower()


def test_vet_logistics_unknown_location(vetter: Vetter) -> None:
    passed, reason = vetter.vet_logistics({"location": "London, UK"})
    assert passed is False
    assert "not in accepted geo scope" in reason.lower()


def test_vet_logistics_remote_policy_fallback(vetter: Vetter) -> None:
    """Location field absent but remote_policy is EMEA — should pass."""
    passed, reason = vetter.vet_logistics({"location": "", "remote_policy": "Remote - EMEA"})
    assert passed is True


def test_vet_skills_security_title(vetter: Vetter) -> None:
    passed, reason = vetter.vet_skills("Senior Security Engineer")
    assert passed is True
    assert "security" in reason.lower()


def test_vet_skills_python_title(vetter: Vetter) -> None:
    passed, reason = vetter.vet_skills("Python Backend Developer")
    assert passed is True
    assert "python" in reason.lower()


def test_vet_skills_no_match(vetter: Vetter) -> None:
    passed, reason = vetter.vet_skills("Frontend Developer (React)")
    assert passed is False
    assert "no core profile match" in reason.lower()


def test_vet_full_pipeline_pass(vetter: Vetter) -> None:
    job = {"title": "Python Security Architect", "location": "Remote EMEA"}
    passed, reason = vetter.vet(job)
    assert passed is True


def test_vet_full_pipeline_blocked_location(vetter: Vetter) -> None:
    job = {"title": "Senior Security Engineer", "location": "Remote US"}
    passed, reason = vetter.vet(job)
    assert passed is False


def test_vet_full_pipeline_blocked_skills(vetter: Vetter) -> None:
    job = {"title": "Frontend Developer", "location": "Zurich, Switzerland"}
    passed, reason = vetter.vet(job)
    assert passed is False
