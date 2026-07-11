"""Authentication middleware for enterprise SSO/OIDC and CI API keys."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from misra_platform.core.config import Settings, get_settings
from misra_platform.core.security import OidcAuthenticator

PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/health/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()
        self.authenticator = OidcAuthenticator(self.settings)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in PUBLIC_PATHS or not self.settings.auth_required:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        api_user = self.authenticator.validate_api_key(api_key)
        if api_user:
            request.state.user = api_user
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                request.state.user = await self.authenticator.validate_bearer_token(token)
                return await call_next(request)
            except ValueError as error:
                return JSONResponse(status_code=401, content={"detail": str(error)})

        if not self.authenticator.enabled:
            request.state.user = await self.authenticator.validate_bearer_token("")
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required. Provide Bearer token or X-API-Key."},
        )
