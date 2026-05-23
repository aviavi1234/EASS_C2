import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter for local demos (per client IP)."""

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60
        hits = [t for t in self._hits[client_ip] if t > window_start]
        self._hits[client_ip] = hits

        limit = settings.rate_limit_per_minute
        remaining = max(0, limit - len(hits))

        if len(hits) >= limit:
            response = Response("Rate limit exceeded", status_code=429)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = "60"
            return response

        self._hits[client_ip].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
        return response
