"""FastAPI application — pipeline API + static frontend."""

from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.deps import PipelineRunner
from api.routes import router
from api.tasks import TaskRegistry

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = ROOT_DIR / "static"
TASKS_FILE = ROOT_DIR / "artifacts" / "tasks.json"


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Optional HTTP Basic auth covering the API and the static UI.

    Enabled by setting RADAR_AUTH_PASSWORD (username defaults to "radar",
    override with RADAR_AUTH_USER). Everything the app serves is personal
    data or a mutating endpoint, so nothing is exempted.
    """

    def __init__(self, app, username: str, password: str) -> None:
        super().__init__(app)
        self._expected = base64.b64encode(f"{username}:{password}".encode()).decode()

    async def dispatch(self, request: Request, call_next):
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic ") and secrets.compare_digest(
            header.removeprefix("Basic "), self._expected
        ):
            return await call_next(request)
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="ai-app-radar"'},
        )


def create_app() -> FastAPI:
    app = FastAPI(title="Pipeline API", version=os.environ.get("APP_VERSION", "dev"))
    app.include_router(router, prefix="/api")

    auth_password = os.environ.get("RADAR_AUTH_PASSWORD")
    if auth_password:
        app.add_middleware(
            BasicAuthMiddleware,
            username=os.environ.get("RADAR_AUTH_USER", "radar"),
            password=auth_password,
        )

    STATIC_DIR.mkdir(exist_ok=True)
    app.state.runner = PipelineRunner(ROOT_DIR)
    app.state.registry = TaskRegistry(path=TASKS_FILE)
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()
