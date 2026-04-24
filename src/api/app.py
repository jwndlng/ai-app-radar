"""FastAPI application — pipeline API + static frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.deps import PipelineRunner
from api.routes import router
from api.tasks import TaskRegistry

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = ROOT_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Pipeline API", version="1.0.0")
    app.include_router(router, prefix="/api")

    STATIC_DIR.mkdir(exist_ok=True)
    app.state.runner = PipelineRunner(ROOT_DIR)
    app.state.registry = TaskRegistry()
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()
