"""Enterprise SSO/OIDC authentication helpers.

Supports OIDC bearer tokens and service API keys. When OIDC is disabled
(development), requests proceed without authentication.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from jose import JWTError, jwt

from misra_platform.core.config import Settings


@dataclass(slots=True)
class AuthenticatedUser:
    user_id: str
    display_name: str
    email: str | None
    roles: list[str]
    auth_method: str


class OidcAuthenticator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks: dict | None = None

    @property
    def enabled(self) -> bool:
        return self.settings.oidc_enabled

    async def _fetch_jwks(self) -> dict:
        if self._jwks:
            return self._jwks
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.settings.oidc_jwks_uri)
            response.raise_for_status()
            self._jwks = response.json()
        return self._jwks

    async def validate_bearer_token(self, token: str) -> AuthenticatedUser:
        if not self.enabled:
            return AuthenticatedUser(
                user_id="dev-user",
                display_name="Development User",
                email=None,
                roles=["reviewer", "admin"],
                auth_method="disabled",
            )

        try:
            jwks = await self._fetch_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=self.settings.oidc_algorithms,
                audience=self.settings.oidc_audience,
                issuer=self.settings.oidc_issuer,
            )
        except (JWTError, httpx.HTTPError) as error:
            raise ValueError(f"Invalid OIDC token: {error}") from error

        return AuthenticatedUser(
            user_id=payload.get("sub", "unknown"),
            display_name=payload.get("name", payload.get("preferred_username", "User")),
            email=payload.get("email"),
            roles=payload.get("roles", payload.get("groups", ["reviewer"])),
            auth_method="oidc",
        )

    def validate_api_key(self, api_key: str | None) -> AuthenticatedUser | None:
        if not api_key or not self.settings.api_keys:
            return None
        if api_key in self.settings.api_keys:
            return AuthenticatedUser(
                user_id="api-key",
                display_name="CI Service Account",
                email=None,
                roles=["ci", "reviewer"],
                auth_method="api_key",
            )
        return None
