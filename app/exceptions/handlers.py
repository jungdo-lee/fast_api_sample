from datetime import datetime, timezone

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.base import AppException

logger = structlog.get_logger("app.exceptions")


def _sanitize_errors(errors: list[dict]) -> list[dict]:
    """Convert validation errors to JSON-safe format.

    Pydantic model_validator errors include non-serializable objects (e.g. ValueError)
    in the 'ctx' field that orjson cannot serialize.
    """
    sanitized = []
    for err in errors:
        clean = {k: v for k, v in err.items() if k != "ctx"}
        if "ctx" in err:
            clean["ctx"] = {k: str(v) for k, v in err["ctx"].items()}
        sanitized.append(clean)
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> ORJSONResponse:
        trace_id = getattr(request.state, "request_id", None)
        await logger.awarning(
            "AppException",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            trace_id=trace_id,
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": exc.extra_detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        trace_id = getattr(request.state, "request_id", None)
        return ORJSONResponse(
            status_code=422,
            content={
                "success": False,
                "error_code": "SYS_004",
                "message": "입력값 검증에 실패했습니다",
                "detail": _sanitize_errors(exc.errors()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> ORJSONResponse:
        trace_id = getattr(request.state, "request_id", None)
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_code": f"SYS_{exc.status_code}",
                "message": str(exc.detail),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> ORJSONResponse:
        trace_id = getattr(request.state, "request_id", None)
        await logger.aerror(
            "Unhandled exception",
            error=str(exc),
            error_type=type(exc).__name__,
            trace_id=trace_id,
            exc_info=True,
        )
        return ORJSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "SYS_001",
                "message": "서버 오류가 발생했습니다",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            },
        )
