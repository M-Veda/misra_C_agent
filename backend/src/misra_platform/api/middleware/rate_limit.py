import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from misra_platform.core.config import Settings
from misra_platform.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path.endswith("/health"):
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self.settings.rate_limit_window_seconds
        limit = self.settings.rate_limit_requests

        timestamps = self._requests[client_host]
        while timestamps and now - timestamps[0] > window:
            timestamps.popleft()

        if len(timestamps) >= limit:
            logger.warning("rate_limit_exceeded", client_host=client_host)
            return Response(status_code=429, content="Rate limit exceeded")

        timestamps.append(now)
        return await call_next(request)
