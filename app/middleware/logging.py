import time
from collections.abc import MutableMapping
from typing import Any

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

logger = structlog.get_logger("app.middleware.logging")


class LoggingContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        state = scope.get("state", {})
        request_id = state.get("request_id", "unknown")
        device_id = headers.get(b"x-device-id", b"unknown").decode()
        # client is tuple (host, port) in scope
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=request_id,
            device_id=device_id,
            client_ip=client_ip,
            user_agent=headers.get(b"user-agent", b"unknown").decode(),
            app_version=headers.get(b"x-app-version", b"unknown").decode(),
            os_type=headers.get(b"x-os-type", b"unknown").decode(),
            request_method=scope.get("method", ""),
            request_uri=scope.get("path", ""),
        )

        start_time = time.perf_counter()
        status_code = 500

        async def send_with_logging(message: MutableMapping[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            await logger.ainfo(
                "Request completed",
                status_code=status_code,
                duration_ms=duration_ms,
            )
