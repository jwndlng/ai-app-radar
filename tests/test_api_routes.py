"""Regression tests for API route ordering and data-preserving endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.deps import PipelineRunner
from core.store import ApplicationStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "settings.yaml").write_text(
        "scout:\n"
        "  max_pages: 10\n"
        "notifications:\n"
        "  telegram:\n"
        "    bot_token: SECRET\n"
        "    chat_id: '42'\n"
    )
    app.state.runner = PipelineRunner(tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def store(tmp_path: Path) -> ApplicationStore:
    return ApplicationStore(tmp_path / "artifacts" / "radar.db")


def test_stats_route_not_shadowed_by_job_detail(client: TestClient) -> None:
    """/jobs/stats must be matched before /jobs/{job_id} or it 404s."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    assert "total" in response.json()


def test_settings_round_trip_preserves_notifications(client: TestClient, tmp_path: Path) -> None:
    settings = client.get("/api/settings").json()
    response = client.put("/api/settings", json=settings)
    assert response.status_code == 200
    saved = (tmp_path / "configs" / "settings.yaml").read_text()
    assert "SECRET" in saved


def test_undo_by_state_preserves_extended_fields(client: TestClient, store: ApplicationStore) -> None:
    """Undo-by-state must round-trip full records; the summary projection
    would rewrite each job's data column and wipe all extended fields."""
    store.save_job({
        "id": "acme-eng",
        "company": "Acme",
        "title": "Engineer",
        "state": "rejected",
        "status": "ok",
        "prev_state": "review",
        "description": "keep me",
        "tech_stack": ["Python"],
    })

    response = client.post("/api/jobs/undo-by-state", json={"state": "rejected"})
    assert response.status_code == 200
    assert response.json()["count"] == 1

    job = store.get_by_id("acme-eng")
    assert job["state"] == "review"
    assert job["description"] == "keep me"
    assert job["tech_stack"] == ["Python"]


def test_manual_reject_stamps_vetted_at(client: TestClient, store: ApplicationStore) -> None:
    store.save_job({
        "id": "acme-eng",
        "company": "Acme",
        "title": "Engineer",
        "state": "review",
        "status": "ok",
        "vetted_at": "2020-01-01T00:00:00",
    })

    response = client.post("/api/jobs/acme-eng/state", json={"state": "rejected", "reason": "no"})
    assert response.status_code == 200

    job = store.get_by_id("acme-eng")
    assert job["state"] == "rejected"
    # The archiver ages rejected jobs from vetted_at; it must reflect the
    # rejection time, not the original evaluation time.
    assert job["vetted_at"] > "2020-01-01T00:00:00"


def test_tasks_list_is_summary_projection(client: TestClient) -> None:
    """The 5s-polled list endpoint must not ship full event logs; the
    detail endpoint returns them."""
    from api.app import app
    from api.tasks import TaskRegistry

    registry = TaskRegistry(None)
    app.state.registry = registry
    done_id = registry.create("pipeline_run_all")
    for i in range(300):
        registry.add_event(done_id, {"type": "item_ok", "name": f"job {i}"})
    registry.complete(done_id, {"scout": 1})
    running_id = registry.create("scout_all")
    for i in range(150):
        registry.add_event(running_id, {"type": "item_ok", "name": f"co {i}"})

    tasks = {t["id"]: t for t in client.get("/api/tasks").json()["tasks"]}
    assert tasks[done_id]["events"] == []
    assert tasks[done_id]["event_count"] == 300
    assert len(tasks[running_id]["events"]) == 100
    assert tasks[running_id]["events"][-1]["name"] == "co 149"

    detail = client.get(f"/api/tasks/{done_id}").json()
    assert len(detail["events"]) == 300


def test_task_events_are_capped() -> None:
    from api.tasks import TaskRegistry

    registry = TaskRegistry(None)
    task_id = registry.create("scout_all")
    for i in range(700):
        registry.add_event(task_id, {"i": i})
    events = registry.get(task_id).events
    assert len(events) == 500
    assert events[0]["i"] == 200 and events[-1]["i"] == 699
