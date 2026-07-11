from typing import Any


class PlatformError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(PlatformError):
    pass


class DependencyUnavailableError(PlatformError):
    pass
