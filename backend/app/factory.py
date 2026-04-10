import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.db.init_db import init_db


def _configure_db_logging() -> None:
    level = logging.DEBUG if settings.debug else logging.INFO
    for name in ("app.db", "app.repositories"):
        log = logging.getLogger(name)
        log.setLevel(level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _configure_db_logging()
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = settings.static_path
    templates_dir = settings.templates_path

    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    templates = (
        Jinja2Templates(directory=str(templates_dir)) if templates_dir.is_dir() else None
    )

    app.include_router(api_router, prefix="/api")

    _widget_path = Path(static_dir) / "widget.js"

    @app.get("/widget.js")
    async def serve_widget_js():
        if not _widget_path.is_file():
            return PlainTextResponse(
                "widget.js not found — add frontend/static/widget.js",
                status_code=404,
            )
        return FileResponse(
            _widget_path,
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=300"},
        )

    def _html(template: str, request: Request, **ctx: Any):
        if templates is None:
            return PlainTextResponse(
                "Templates directory not found. Set FRONTEND_TEMPLATES_DIR in .env",
                status_code=503,
            )
        base_ctx = {"request": request, "app_name": settings.app_name}
        base_ctx.update(ctx)
        return templates.TemplateResponse(template, base_ctx)

    @app.get("/")
    async def root(request: Request):
        return _html("index.html", request, page_title="Klyro")

    @app.get("/pricing")
    async def pricing_page(request: Request):
        return _html("pricing.html", request, page_title="Pricing")

    @app.get("/login")
    async def login_page(request: Request):
        return _html("login.html", request, page_title="Log in")

    @app.get("/signup")
    async def signup_page(request: Request):
        return _html("signup.html", request, page_title="Sign up")

    @app.get("/dashboard")
    async def dashboard_page(request: Request):
        return _html(
            "dashboard.html",
            request,
            page_title="Dashboard",
            hide_nav=True,
            hide_footer=True,
        )

    @app.get("/chatbot/create")
    async def chatbot_create_page(request: Request):
        return _html(
            "chatbot-create.html",
            request,
            page_title="Create chatbot",
            hide_nav=True,
            hide_footer=True,
        )

    @app.get("/chatbot/{chatbot_id:int}")
    async def chatbot_detail_page(request: Request, chatbot_id: int):
        return _html(
            "chatbot-detail.html",
            request,
            page_title="Chatbot",
            chatbot_id=chatbot_id,
            hide_nav=True,
            hide_footer=True,
        )

    return app
