import logging
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.api import health, posts
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.metrics import setup_metrics
from app.middleware.logging_middleware import RequestLoggingMiddleware

setup_logging(
    log_level=settings.LOG_LEVEL,
    json_logs=(settings.ENVIRONMENT != "development"),
)

logger = structlog.get_logger(__name__)


def _init_sentry() -> None:
    if not settings.SENTRY_DSN:
        logger.info("sentry_disabled", reason="SENTRY_DSN not configured")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.WARNING,    # capture as breadcrumb
                event_level=logging.ERROR,  # send as Sentry event
            ),
        ],
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        send_default_pii=False,
    )
    logger.info("sentry_initialized", environment=settings.ENVIRONMENT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", name=settings.APP_NAME, env=settings.ENVIRONMENT)
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    _init_sentry()

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs"  if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    app.add_middleware(RequestLoggingMiddleware)

    # Prometheus — must be set up before routes are registered
    instrumentator = setup_metrics(app)
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

    app.include_router(health.router)
    app.include_router(posts.router)

    return app


app = create_app()
