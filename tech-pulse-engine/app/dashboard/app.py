from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config.settings import Settings, load_settings
from app.db.session import create_session_factory, session_scope
from app.services.monitoring import build_dashboard_snapshot
from app.services.opportunities import get_opportunity, refresh_templates, serialize_opportunity_detail, set_status


def create_dashboard_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    session_factory = create_session_factory(resolved_settings.database_url)
    dashboard_dir = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(dashboard_dir / "templates"))

    app = FastAPI(title=resolved_settings.dashboard_title, version="2.0.0")
    app.mount("/static", StaticFiles(directory=str(dashboard_dir / "static")), name="static")

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard", status_code=302)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/dashboard/summary")
    async def summary() -> JSONResponse:
        with session_scope(session_factory) as session:
            snapshot = build_dashboard_snapshot(session)
        return JSONResponse(snapshot)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        with session_scope(session_factory) as session:
            snapshot = build_dashboard_snapshot(session)
        context = {
            "request": request,
            "snapshot": snapshot,
            "settings": resolved_settings,
        }
        return templates.TemplateResponse("dashboard.html", context)

    @app.get("/opportunities/{opportunity_id}", response_class=HTMLResponse)
    async def opportunity_detail(request: Request, opportunity_id: int, notice: str | None = None) -> HTMLResponse:
        with session_scope(session_factory) as session:
            opportunity = get_opportunity(session, opportunity_id)
            if opportunity is None:
                raise HTTPException(status_code=404, detail="Opportunity not found")
            context = {
                "request": request,
                "settings": resolved_settings,
                "opportunity": serialize_opportunity_detail(opportunity),
                "notice": notice,
            }
        return templates.TemplateResponse("opportunity.html", context)

    @app.post("/opportunities/{opportunity_id}/compose")
    async def compose_opportunity(opportunity_id: int) -> RedirectResponse:
        with session_scope(session_factory) as session:
            opportunity = get_opportunity(session, opportunity_id)
            if opportunity is None:
                raise HTTPException(status_code=404, detail="Opportunity not found")
            refresh_templates(opportunity)
        return RedirectResponse(url=f"/opportunities/{opportunity_id}?notice=Templates refreshed", status_code=303)

    @app.post("/opportunities/{opportunity_id}/status/{status}")
    async def update_opportunity_status(opportunity_id: int, status: str) -> RedirectResponse:
        with session_scope(session_factory) as session:
            opportunity = get_opportunity(session, opportunity_id)
            if opportunity is None:
                raise HTTPException(status_code=404, detail="Opportunity not found")
            set_status(opportunity, status)
        return RedirectResponse(url=f"/opportunities/{opportunity_id}?notice=Status updated", status_code=303)

    return app


def serve_dashboard(settings: Settings | None = None, host: str | None = None, port: int | None = None) -> None:
    resolved_settings = settings or load_settings()
    app = create_dashboard_app(resolved_settings)
    uvicorn.run(
        app,
        host=host or resolved_settings.dashboard_host,
        port=port or resolved_settings.dashboard_port,
        log_level=resolved_settings.log_level.lower(),
    )
