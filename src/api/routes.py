"""API route handlers for all pipeline operations."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.deps import PipelineRunner, get_registry, get_runner
from api.tasks import TaskRegistry, make_event_callback, make_progress_callback, run_with_tracking
from core.state_machine import StateMachine

_ALLOWED_MANUAL_STATES = {"rejected", "applied", "match"}

router = APIRouter()


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
async def list_jobs(runner: PipelineRunner = Depends(get_runner)):
    try:
        jobs = runner._store().load()
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, runner: PipelineRunner = Depends(get_runner)):
    store = runner._store()
    jobs = store.load()
    remaining = [j for j in jobs if j.get("id") != job_id]
    if len(remaining) == len(jobs):
        return JSONResponse(status_code=404, content={"detail": "Job not found"})
    store.save(remaining)
    return {"ok": True, "id": job_id}


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks")
async def list_tasks(registry: TaskRegistry = Depends(get_registry)):
    tasks = [t.to_dict() for t in registry.all()]
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, registry: TaskRegistry = Depends(get_registry)):
    record = registry.get(task_id)
    if record is None:
        return JSONResponse(status_code=404, content={"detail": f"Task not found: {task_id}"})
    return record.to_dict()


# ── Scout ─────────────────────────────────────────────────────────────────────

@router.post("/scout/next")
async def scout_next(
    background_tasks: BackgroundTasks,
    body: LimitBody = LimitBody(),
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create(f"scout_next_{body.limit}")
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.scout_next(limit=body.limit,
                                                on_progress=make_progress_callback(registry, task_id),
                                                on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}


@router.post("/scout")
async def scout_all(
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create("scout_all")
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.scout_all(on_progress=make_progress_callback(registry, task_id),
                                               on_event=make_event_callback(registry, task_id)))
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
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.scout_company(company_name,
                                                   on_progress=make_progress_callback(registry, task_id),
                                                   on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}


# ── Enrich ────────────────────────────────────────────────────────────────────

@router.post("/enrich/all")
async def enrich_all(
    background_tasks: BackgroundTasks,
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create("enrich_all")
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.enrich_all(on_progress=make_progress_callback(registry, task_id),
                                                on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}


@router.post("/enrich/next")
async def enrich_next(
    background_tasks: BackgroundTasks,
    body: LimitBody = LimitBody(),
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create(f"enrich_next_{body.limit}")
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.enrich_next(limit=body.limit,
                                                 on_progress=make_progress_callback(registry, task_id),
                                                 on_event=make_event_callback(registry, task_id)))
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
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.evaluate_all(on_progress=make_progress_callback(registry, task_id),
                                                  on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}


@router.post("/evaluate/next")
async def evaluate_next(
    background_tasks: BackgroundTasks,
    body: LimitBody = LimitBody(),
    runner: PipelineRunner = Depends(get_runner),
    registry: TaskRegistry = Depends(get_registry),
):
    task_id = registry.create(f"evaluate_next_{body.limit}")
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.evaluate_next(limit=body.limit,
                                                   on_progress=make_progress_callback(registry, task_id),
                                                   on_event=make_event_callback(registry, task_id)))
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
    jobs = store.load()
    job = next((j for j in jobs if j.get("id") == job_id), None)
    if job is None:
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    job["prev_state"] = job.get("state")
    job["state"] = body.state
    if body.state == "rejected" and body.reason:
        job["rejection_reason"] = body.reason
    elif body.state != "rejected":
        job.pop("rejection_reason", None)
    StateMachine.touch_updated(job)
    store.save(jobs)
    return {"ok": True, "id": job_id, "state": body.state}


# ── Favorites ────────────────────────────────────────────────────────────────

@router.patch("/jobs/{job_id}/favorite")
async def toggle_favorite(
    job_id: str,
    runner: PipelineRunner = Depends(get_runner),
):
    store = runner._store()
    jobs = store.load()
    job = next((j for j in jobs if j.get("id") == job_id), None)
    if job is None:
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    job["favorited"] = not job.get("favorited", False)
    store.save(jobs)
    return {"ok": True, "id": job_id, "favorited": job["favorited"]}


# ── Undo ─────────────────────────────────────────────────────────────────────

@router.post("/jobs/undo-by-state")
async def undo_by_state(
    body: StateBody,
    runner: PipelineRunner = Depends(get_runner),
):
    store = runner._store()
    jobs = store.load()
    count = 0
    for job in jobs:
        if job.get("state") == body.state:
            if runner.undo_job(job) is not None:
                count += 1
    if count:
        store.save(jobs)
    return {"ok": True, "state": body.state, "count": count}


@router.post("/jobs/{job_id}/undo")
async def undo_job(
    job_id: str,
    runner: PipelineRunner = Depends(get_runner),
):
    store = runner._store()
    jobs = store.load()
    job = next((j for j in jobs if j.get("id") == job_id), None)
    if job is None:
        return JSONResponse(status_code=404, content={"detail": f"Job not found: {job_id}"})
    result = runner.undo_job(job)
    if result is None:
        return JSONResponse(status_code=400, content={"detail": "Cannot undo from discovered state"})
    StateMachine.touch_updated(job)
    store.save(jobs)
    return {"ok": True, "id": job_id, "state": job["state"]}


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
    background_tasks.add_task(run_with_tracking, registry, task_id,
                              runner.run_job(job_id, on_event=make_event_callback(registry, task_id)))
    return {"ok": True, "task_id": task_id}
