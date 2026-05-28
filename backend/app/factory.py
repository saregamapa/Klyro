import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.services.job_worker import run_worker_loop


def _configure_db_logging() -> None:
    level = logging.DEBUG if settings.debug else logging.INFO
    log_format = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Set up console handler with structured format
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Configure app-specific loggers
    for name in ("app.db", "app.repositories"):
        log = logging.getLogger(name)
        log.setLevel(level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _configure_db_logging()
    init_db()
    worker_task = asyncio.create_task(run_worker_loop())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            send_default_pii=False,
        )
        logging.getLogger(__name__).info(
            "Sentry initialised (environment=%s)", settings.environment
        )

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
    )

    app.state.limiter = limiter

    # Add rate limit exception handler
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60"},
        )

    # Add middleware for request IDs
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

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
        base_ctx = {"app_name": settings.app_name}
        base_ctx.update(ctx)
        return templates.TemplateResponse(request, template, base_ctx)

    @app.get("/")
    async def root(request: Request):
        return _html("index.html", request, page_title="Klyro")

    @app.get("/pricing")
    async def pricing_page(request: Request):
        return _html("pricing.html", request, page_title="Pricing")

    @app.get("/login")
    async def login_page(request: Request):
        return _html("login.html", request, page_title="Log in")

    @app.get("/forgot-password")
    async def forgot_password_page(request: Request):
        return _html("forgot-password.html", request, page_title="Reset password")

    @app.get("/reset-password")
    async def reset_password_page(request: Request, token: str = ""):
        return _html(
            "reset-password.html",
            request,
            page_title="Set new password",
            token=token,
        )

    @app.get("/signup")
    async def signup_page(request: Request):
        return _html("signup.html", request, page_title="Sign up")

    @app.get("/billing")
    async def billing_page(request: Request):
        return _html(
            "billing.html",
            request,
            page_title="Billing",
            hide_nav=True,
            hide_footer=True,
        )

    @app.get("/dashboard")
    async def dashboard_page(request: Request):
        return _html(
            "dashboard.html",
            request,
            page_title="Dashboard",
            hide_nav=True,
            hide_footer=True,
        )

    @app.get("/dashboard/analytics")
    async def analytics_page(request: Request):
        return _html(
            "analytics.html",
            request,
            page_title="Analytics",
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
