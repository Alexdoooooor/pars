from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from server.config import get_settings
from server.db import get_connection
from server.routes.analytics import router as analytics_router
from server.routes.automation import router as automation_router
from server.routes.scenarios import router as scenarios_router
from server.schemas import HealthOut, PublicStatusOut
from server.services.bootstrap_schema import ensure_schema_applied
from server.services.scheduler import scheduler_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def _lifespan_scheduler(_app: FastAPI):
    try:
        await asyncio.to_thread(ensure_schema_applied)
    except Exception:
        logger.exception("schema bootstrap failed")
    task = asyncio.create_task(scheduler_loop(), name="pi_scheduler")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def register_api_routes(app: FastAPI) -> None:
    @app.get("/api/public-config.js")
    def public_config_js() -> Response:
        s = get_settings()
        base = (s.app_base_url or "").strip().rstrip("/")
        body = "window.__PI_BASE__=" + json.dumps(base, ensure_ascii=False) + ";"
        return Response(
            content=body,
            media_type="application/javascript; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/public/status", response_model=PublicStatusOut)
    def public_status() -> PublicStatusOut:
        s = get_settings()
        if not s.db_user:
            return PublicStatusOut(service="price-intelligence", db=False, ok=False, detail="DB_USER не задан")
        try:
            with get_connection(s) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return PublicStatusOut(service="price-intelligence", db=True, ok=True, detail=None)
        except Exception as e:
            logger.warning("public status db fail: %s", e)
            return PublicStatusOut(service="price-intelligence", db=False, ok=False, detail=str(e))

    @app.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        s = get_settings()
        if not s.db_user:
            return HealthOut(ok=False, db=False, detail="DB_USER не задан")
        try:
            with get_connection(s) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return HealthOut(ok=True, db=True)
        except Exception as e:
            logger.warning("health db fail: %s", e)
            return HealthOut(ok=False, db=False, detail=str(e))

    app.include_router(scenarios_router)
    app.include_router(analytics_router)
    app.include_router(automation_router)


def _make_inner_app(*, with_lifespan: bool) -> FastAPI:
    kw: dict = {"title": "VTB Price Intelligence", "version": "1.0.0"}
    if with_lifespan:
        kw["lifespan"] = _lifespan_scheduler
    app = FastAPI(**kw)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_api_routes(app)
    app.mount(
        "/",
        StaticFiles(directory=str(ROOT), html=True),
        name="static",
    )
    return app


def create_app() -> FastAPI:
    settings = get_settings()
    raw = (settings.app_base_url or "").strip()
    prefix = raw.rstrip("/")
    if prefix and not prefix.startswith("/"):
        prefix = "/" + prefix

    if prefix:
        inner = _make_inner_app(with_lifespan=False)
        root = FastAPI(lifespan=_lifespan_scheduler, title="VTB Price Intelligence", version="1.0.0")
        root.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @root.get("/", include_in_schema=False)
        def _redirect_root_to_app() -> RedirectResponse:
            return RedirectResponse(url=f"{prefix}/index.html", status_code=307)

        root.mount(prefix, inner)
        return root

    return _make_inner_app(with_lifespan=True)


app = create_app()
