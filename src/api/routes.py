"""API route handlers for all pipeline operations."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.deps import PipelineRunner, get_registry, get_runner
from api.tasks import TaskRegistry, make_event_callback, make_progress_callback, run_with_tracking
from core.state_machine import StateMachine

_ALLOWED_MANUAL_STATES = {"rejected", "applied", "match"}

router = APIRouter()


@router.get("/version")
def get_version() -> dict:
    return {"version": os.environ.get("APP_VERSION", "dev")}


class LimitBody(BaseModel):
    limit: int = 10


class EnabledBody(BaseModel):
    enabled: bool


class RestoreBody(BaseModel):
    filename: str


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(runner: PipelineRunner = Depends(get_runner)):
    try:
        return runner.load_settings()
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.put("/settings")
async def save_settings(
    body: dict = Body(...),
    runner: PipelineRunner = Depends(get_runner),
):
    try:
        runner.save_settings(body)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# ── Companies ─────────────────────────────────────────────────────────────────

@router.get("/companies")
async def list_companies(runner: PipelineRunner = Depends(get_runner)):
    try:
        companies = runner.list_companies()
        return {"companies": companies, "total": len(companies)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.patch("/companies/{name}")
async def set_company_enabled(
    name: str,
    body: EnabledBody,
    runner: PipelineRunner = Depends(get_runner),
):
    found = runner.set_company_enabled(name, body.enabled)
    if not found:
        return JSONResponse(status_code=404, content={"detail": f"Company not found: {name}"})
    return {"ok": True, "name": name, "enabled": body.enabled}


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(runner: PipelineRunner = Depends(get_runner)):
    data = runner.load_profile()
    if data is None:
        return JSONResponse(status_code=404, content={"detail": "Profile not found"})
    return data


@router.put("/profile")
async def update_profile(
    body: dict = Body(...),
    runner: PipelineRunner = Depends(get_runner),
):
    try:
        runner.save_profile(body)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.get("/profile/backups")
async def list_profile_backups(runner: PipelineRunner = Depends(get_runner)):
    return {"backups": runner.list_backups()}


@router.post("/profile/backups/restore")
async def restore_profile_backup(
    body: RestoreBody,
    runner: PipelineRunner = Depends(get_runner),
):
    if ".." in body.filename or "/" in body.filename or "\\" in body.filename:
        return JSONResponse(status_code=400, content={"detail": "Invalid filename"})
    if not runner.restore_backup(body.filename):
        return JSONResponse(status_code=404, content={"detail": "Backup not found"})
    return {"ok": True, "restored": body.filename}


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(
    state: str | None = None,
    status: str | None = None,
    search: str | None = None,
    favorited_only: bool = False,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    projection: str = "summary",
    limit: int | None = None,
    offset: int = 0,
    runner: PipelineRunner = Depends(get_runner),
):
    try:
        store = runner._store()
        jobs = store.list_jobs(
            state=state,
            status=status,
            search=search,
            favorited_only=favorited_only,
            sort_by=sort_by,
            sort_order=sort_order,
            projection=projection,
            limit=limit,
            offset=offset,
        )
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# /jobs/stats must be registered before /jobs/{job_id}, or FastAPI matches
# "stats" as a job_id and the endpoint 404s.
@router.get("/jobs/stats")
async def get_job_stats(runner: PipelineRunner = Depends(get_runner)):
    try:
        stats = runner._store().state_counts()
        return stats
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.get("/jobs/{job_id}")
async def get_job_detail(
    job_id: str,
    runner: PipelineRunner = Depends(get_runner),
):
    try:
        store = runner._store()
        job = store.get_by_id(job_id)
        if job is None:
            return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
        return job
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, runner: PipelineRunner = Depends(get_runner)):
    store = runner._store()
    deleted = store.delete_job(job_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"detail": "Job not found"})
    return {"ok": True, "id": job_id}


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks")
async def list_tasks(registry: TaskRegistry = Depends(get_registry)):
    # Summary projection: the frontend polls this every 5 seconds, so full
    # event logs (MBs across 100 records) must not be shipped here — the
    # detail endpoint below returns them for a single task.
    tasks = [t.to_summary_dict() for t in registry.all()]
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, registry: TaskRegistry = Depends(get_registry)):
    record = registry.get(task_id)
    if record is None:
        return JSONResponse(status_code=404, content={"detail": f"Task not found: {task_id}"})
    return record.to_dict()


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, registry: TaskRegistry = Depends(get_registry)):
    record = registry.get(task_id)
    if record is None:
        return JSONResponse(status_code=404, content={"detail": f"Task not found: {task_id}"})
    if record.status in {"done", "failed", "cancelled"}:
        return JSONResponse(status_code=409, content={"detail": f"Task is already {record.status}"})
    registry.cancel(task_id)
    return {"ok": True}


# ── Scout ─────────────────────────────────────────────────────────────────────

@router.post("/scout/next")
async def scout_next(
    background_tasks: BackgroundTasks,
    body: LimitBody = LimitBody(),
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create(f"scout_next_{body.limit}")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.scout_next(limit=body.limit,
                                                on_progress=make_progress_callback(registry, task_id),
                                                on_event=make_event_callback(registry, task_id),
                                                should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


@router.post("/scout")
async def scout_all(
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create("scout_all")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.scout_all(on_progress=make_progress_callback(registry, task_id),
                                               on_event=make_event_callback(registry, task_id),
                                               should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


@router.post("/scout/{company_name}")
async def scout_company(
    company_name: str,
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    if company_name.lower() not in runner._company_names():
        return JSONResponse(status_code=404, content={"detail": f"Company not found: {company_name}"})
    task_id = registry.create(f"scout_{company_name}")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.scout_company(company_name,
                                                   on_progress=make_progress_callback(registry, task_id),
                                                   on_event=make_event_callback(registry, task_id),
                                                   should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


# ── Enrich ────────────────────────────────────────────────────────────────────

@router.post("/enrich/all")
async def enrich_all(
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create("enrich_all")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.enrich_all(on_progress=make_progress_callback(registry, task_id),
                                                on_event=make_event_callback(registry, task_id),
                                                should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


@router.post("/enrich/next")
async def enrich_next(
    background_tasks: BackgroundTasks,
    body: LimitBody = LimitBody(),
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create(f"enrich_next_{body.limit}")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.enrich_next(limit=body.limit,
                                                 on_progress=make_progress_callback(registry, task_id),
                                                 on_event=make_event_callback(registry, task_id),
                                                 should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


@router.post("/enrich/{job_id}")
async def enrich_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    jobs = runner._store().load()
    if not any(j.get("id") == job_id for j in jobs):
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    task_id = registry.create(f"enrich_{job_id}")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.enrich_job(job_id, on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}


# ── Evaluate ──────────────────────────────────────────────────────────────────

@router.post("/evaluate/all")
async def evaluate_all(
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create("evaluate_all")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.evaluate_all(on_progress=make_progress_callback(registry, task_id),
                                                  on_event=make_event_callback(registry, task_id),
                                                  should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


@router.post("/evaluate/next")
async def evaluate_next(
    background_tasks: BackgroundTasks,
    body: LimitBody = LimitBody(),
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create(f"evaluate_next_{body.limit}")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.evaluate_next(limit=body.limit,
                                                   on_progress=make_progress_callback(registry, task_id),
                                                   on_event=make_event_callback(registry, task_id),
                                                   should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


@router.post("/evaluate/{job_id}")
async def evaluate_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    jobs = runner._store().load()
    if not any(j.get("id") == job_id for j in jobs):
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    task_id = registry.create(f"evaluate_{job_id}")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.evaluate_job(job_id, on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}


# ── Manual state transitions ──────────────────────────────────────────────────

class StateBody(BaseModel):
    state: str
    reason: str | None = None


@router.post("/jobs/{job_id}/state")
async def set_job_state(
    job_id: str,
    body: StateBody,
    runner: PipelineRunner = Depends(get_runner),
):
    if body.state not in _ALLOWED_MANUAL_STATES:
        return JSONResponse(status_code=400, content={"detail": f"Invalid state: {body.state}"})
    store = runner._store()
    job = store.get_by_id(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    job["prev_state"] = job.get("state")
    job["state"] = body.state
    if body.state == "rejected":
        # Stamp the rejection time: the archiver ages rejected jobs from
        # vetted_at, which otherwise still holds the original evaluation time.
        job["vetted_at"] = datetime.now().isoformat()
        if body.reason:
            job["rejection_reason"] = body.reason
    else:
        job.pop("rejection_reason", None)
    StateMachine.touch_updated(job)
    store.save_job(job)
    return {"ok": True, "id": job_id, "state": body.state}


# ── Favorites ────────────────────────────────────────────────────────────────

@router.patch("/jobs/{job_id}/favorite")
async def toggle_favorite(
    job_id: str,
    runner: PipelineRunner = Depends(get_runner),
):
    store = runner._store()
    job = store.get_by_id(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    job["favorited"] = not job.get("favorited", False)
    store.save_job(job)
    return {"ok": True, "id": job_id, "favorited": job["favorited"]}


# ── Bulk edit ────────────────────────────────────────────────────────────────

_BULK_ACTIONS = {"set_state", "favorite", "unfavorite", "delete"}


class BulkBody(BaseModel):
    ids: list[str]
    action: str
    state: str | None = None
    reason: str | None = None


@router.post("/jobs/bulk")
async def bulk_edit_jobs(
    body: BulkBody,
    runner: PipelineRunner = Depends(get_runner),
):
    if body.action not in _BULK_ACTIONS:
        return JSONResponse(status_code=400, content={"detail": f"Invalid action: {body.action}"})
    if body.action == "set_state" and body.state not in _ALLOWED_MANUAL_STATES:
        return JSONResponse(status_code=400, content={"detail": f"Invalid state: {body.state}"})

    store = runner._store()
    updated = 0
    missing: list[str] = []
    to_save: list[dict] = []

    for job_id in body.ids:
        if body.action == "delete":
            if store.delete_job(job_id):
                updated += 1
            else:
                missing.append(job_id)
            continue

        job = store.get_by_id(job_id)
        if job is None:
            missing.append(job_id)
            continue

        if body.action == "set_state":
            job["prev_state"] = job.get("state")
            job["state"] = body.state
            if body.state == "rejected":
                # Same semantics as the single-job route: stamp the rejection
                # time so the archiver ages from it.
                job["vetted_at"] = datetime.now().isoformat()
                if body.reason:
                    job["rejection_reason"] = body.reason
            else:
                job.pop("rejection_reason", None)
        elif body.action == "favorite":
            job["favorited"] = True
        elif body.action == "unfavorite":
            job["favorited"] = False

        StateMachine.touch_updated(job)
        to_save.append(job)
        updated += 1

    if to_save:
        store.save(to_save)
    return {"ok": True, "updated": updated, "missing": missing}


# ── Maintenance ──────────────────────────────────────────────────────────────

@router.post("/maintenance/cleanup")
async def run_cleanup(runner: PipelineRunner = Depends(get_runner)):
    try:
        archived = runner.run_cleanup()
        return {"ok": True, "archived": archived}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# ── Undo ─────────────────────────────────────────────────────────────────────

@router.post("/jobs/undo-by-state")
async def undo_by_state(
    body: StateBody,
    runner: PipelineRunner = Depends(get_runner),
):
    store = runner._store()
    # Full projection is required: saving summary rows back would rewrite each
    # job's data column from the projected dict and wipe all extended fields.
    jobs = store.list_jobs(state=body.state, projection="full")
    count = 0
    to_save = []
    for job in jobs:
        if runner.undo_job(job) is not None:
            count += 1
            StateMachine.touch_updated(job)
            to_save.append(job)
    if to_save:
        store.save(to_save)
    return {"ok": True, "state": body.state, "count": count}


@router.post("/jobs/{job_id}/undo")
async def undo_job(
    job_id: str,
    runner: PipelineRunner = Depends(get_runner),
):
    store = runner._store()
    job = store.get_by_id(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    result = runner.undo_job(job)
    if result is None:
        return JSONResponse(status_code=400, content={"detail": "Cannot undo from discovered state"})
    StateMachine.touch_updated(job)
    store.save_job(job)
    return {"ok": True, "id": job_id, "state": job["state"]}


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.post("/pipeline/all")
async def pipeline_all(
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create("pipeline_run_all")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.run_all(on_progress=make_progress_callback(registry, task_id),
                                             on_event=make_event_callback(registry, task_id),
                                             should_cancel=event.is_set))
    return {"ok": True, "task_id": task_id}


# ── Run all remaining ─────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/run")
async def run_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    jobs = runner._store().load()
    if not any(j.get("id") == job_id for j in jobs):
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    task_id = registry.create(f"run_{job_id}")
    event = asyncio.Event()
    registry.register_event(task_id, event)
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.run_job(job_id, on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}
