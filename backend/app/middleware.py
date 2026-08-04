"""Middleware: request logging and basic rate limiting.

- LoggingMiddleware logs method, path, status and duration for every request.
- RateLimitMiddleware enforces a simple fixed-window per-IP limit so a
  single client can't hammer the (potentially paid) LLM endpoints.
"""

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one line per request with status and elapsed time."""

    async def dispatch(self, request: Request, call_next) -> Response:
        import logging

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logging.getLogger("app.access").info(
            f'{request.method} {request.url.path} -> {response.status_code} '
            f'({elapsed_ms:.0f}ms)'
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter keyed by client IP.

    When the limit is exceeded a 429 is returned with a `Retry-After`
    header. The window resets automatically after `window_seconds`.
    """

    def __init__(self, app, max_requests: int | None = None, window_seconds: int | None = None):
        super().__init__(app)
        # Tuneable at construction time; falls back to settings.
        self.max_requests = (
            max_requests if max_requests is not None else settings.rate_limit_requests
        )
        self.window_seconds = (
            window_seconds if window_seconds is not None else settings.rate_limit_window_seconds
        )
        # ip -> (window_start, request_count)
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for non-API and streaming-less probes.
        if not request.url.path.startswith("/api/v1"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            window_start, count = self._hits.get(client_ip, (now, 0))
            if now - window_start >= self.window_seconds:
                window_start, count = now, 0
            count += 1
            self._hits[client_ip] = (window_start, count)

        if count > self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - window_start)))
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded: {self.max_requests} requests per "
                        f"{self.window_seconds}s. Try again shortly."
                    )
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
