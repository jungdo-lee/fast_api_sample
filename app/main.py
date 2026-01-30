from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.core.redis import close_redis, init_redis
from app.exceptions.handlers import register_exception_handlers
from app.middleware.logging import LoggingContextMiddleware
from app.middleware.request_id import RequestIdMiddleware

settings = get_settings()
logger = structlog.get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(json_logs=settings.log_json, log_level=settings.log_level)
    await logger.ainfo("Starting application", environment=settings.environment)

    await init_db()
    await logger.ainfo("Database initialized")

    from app.services.jwt import get_jwt_service
    jwt_svc = get_jwt_service()
    jwt_svc.validate_keys()
    await logger.ainfo("JWT keys validated")

    try:
        await init_redis()
        await logger.ainfo("Redis connected")
    except Exception as e:
        await logger.awarning("Redis connection failed, running without Redis", error=str(e))

    yield

    await close_redis()
    await logger.ainfo("Application shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Add rate limiter state and exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Middleware is added in LIFO order (last added runs first on inbound request).
    # Execution order: RequestIdMiddleware -> LoggingContextMiddleware -> CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingContextMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
