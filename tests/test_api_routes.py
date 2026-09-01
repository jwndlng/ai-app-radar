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
    # Finished tasks keep a short tail (the UI renders summaries/failures
    # from the polled list), not the full log.
    assert len(tasks[done_id]["events"]) == 20
    assert tasks[done_id]["events"][-1]["name"] == "job 299"
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


def test_bulk_reject_stamps_and_saves(client: TestClient, store: ApplicationStore) -> None:
    for i in range(3):
        store.save_job({
            "id": f"j{i}", "company": "Acme", "title": f"Role {i}",
            "state": "review", "status": "ok", "description": "keep me",
        })

    response = client.post("/api/jobs/bulk", json={
        "ids": ["j0", "j1", "ghost"], "action": "set_state",
        "state": "rejected", "reason": "not a fit",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["updated"] == 2
    assert body["missing"] == ["ghost"]

    for jid in ("j0", "j1"):
        job = store.get_by_id(jid)
        assert job["state"] == "rejected"
        assert job["prev_state"] == "review"
        assert job["rejection_reason"] == "not a fit"
        assert job["vetted_at"]
        assert job["description"] == "keep me"
    assert store.get_by_id("j2")["state"] == "review"


def test_bulk_favorite_and_delete(client: TestClient, store: ApplicationStore) -> None:
    for i in range(2):
        store.save_job({"id": f"j{i}", "company": "A", "title": f"T{i}",
                        "state": "discovered", "status": "ok"})

    r = client.post("/api/jobs/bulk", json={"ids": ["j0", "j1"], "action": "favorite"})
    assert r.json()["updated"] == 2
    assert store.get_by_id("j0")["favorited"] is True

    r = client.post("/api/jobs/bulk", json={"ids": ["j0"], "action": "delete"})
    assert r.json()["updated"] == 1
    assert store.get_by_id("j0") is None
    assert store.get_by_id("j1") is not None


def test_bulk_rejects_invalid_action_and_state(client: TestClient) -> None:
    assert client.post("/api/jobs/bulk", json={"ids": ["x"], "action": "explode"}).status_code == 400
    assert client.post("/api/jobs/bulk", json={
        "ids": ["x"], "action": "set_state", "state": "discovered",
    }).status_code == 400


def test_maintenance_cleanup_endpoint(client: TestClient, store: ApplicationStore, tmp_path: Path) -> None:
    (tmp_path / "configs" / "settings.yaml").write_text(
        "archival:\n  rejected_after_days: 30\n  failed_after_days: 60\n"
    )
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    store.save_job({"id": "old-rej", "company": "A", "title": "T1",
                    "state": "rejected", "status": "ok", "vetted_at": old})
    store.save_job({"id": "old-fail", "company": "A", "title": "T2",
                    "state": "discovered", "status": "failed", "updated_at": old})
    store.save_job({"id": "fresh", "company": "A", "title": "T3",
                    "state": "discovered", "status": "ok"})

    response = client.post("/api/maintenance/cleanup")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "archived": 2}
    assert store.get_by_id("old-rej") is None
    assert store.get_by_id("old-fail") is None
    assert store.get_by_id("fresh") is not None


def test_bulk_rereject_preserves_prev_state_and_archiver_clock(
    client: TestClient, store: ApplicationStore
) -> None:
    """Re-applying a state must not clobber prev_state, and a manual state
    change clears a stale archived_at (which would win the archiver's age
    computation over the fresh rejection stamp)."""
    store.save_job({
        "id": "j1", "company": "A", "title": "T", "state": "rejected",
        "status": "ok", "prev_state": "review",
        "archived_at": "2020-01-01T00:00:00", "vetted_at": "2026-01-01T00:00:00",
    })

    client.post("/api/jobs/bulk", json={"ids": ["j1"], "action": "set_state", "state": "rejected"})
    job = store.get_by_id("j1")
    assert job["prev_state"] == "review"
    assert "archived_at" not in job


def test_undo_by_state_rejects_wildcards(client: TestClient) -> None:
    assert client.post("/api/jobs/undo-by-state", json={"state": "all"}).status_code == 400
    assert client.post("/api/jobs/undo-by-state", json={"state": "bogus"}).status_code == 400


def test_whole_store_operations_conflict_when_one_runs(client: TestClient) -> None:
    from api.app import app
    from api.tasks import TaskRegistry

    registry = TaskRegistry(None)
    app.state.registry = registry
    registry.create("enrich_all")  # stays running

    r = client.post("/api/scout")
    assert r.status_code == 409
    assert "already running" in r.json()["detail"]


def test_registry_eviction_keeps_running_tasks() -> None:
    from api.tasks import TaskRegistry

    registry = TaskRegistry(None)
    running_id = registry.create("pipeline_run_all")
    for i in range(120):
        tid = registry.create(f"scout_x{i}")
        registry.complete(tid, {})
    assert len(registry.all()) == TaskRegistry._MAX
    assert registry.get(running_id) is not None
    assert registry.get(running_id).status == "running"


def test_basic_auth_middleware(tmp_path: Path, monkeypatch) -> None:
    import base64
    import importlib

    monkeypatch.setenv("RADAR_AUTH_PASSWORD", "hunter2")
    import api.app as app_module
    importlib.reload(app_module)
    try:
        from api.deps import PipelineRunner
        (tmp_path / "artifacts").mkdir()
        (tmp_path / "configs").mkdir()
        app_module.app.state.runner = PipelineRunner(tmp_path)
        with TestClient(app_module.app) as c:
            assert c.get("/api/jobs/stats").status_code == 401
            token = base64.b64encode(b"radar:hunter2").decode()
            ok = c.get("/api/jobs/stats", headers={"Authorization": f"Basic {token}"})
            assert ok.status_code == 200
    finally:
        monkeypatch.delenv("RADAR_AUTH_PASSWORD")
        importlib.reload(app_module)
