from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from misra_platform.core.enums import Environment


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MISRA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "MISRA Compliance Platform"
    version: str = "1.0.0-rc1"
    environment: Environment = Environment.DEVELOPMENT
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://misra:misra_dev_password@localhost:5432/misra_platform"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_health_timeout_seconds: float = 2.0

    clang_worker_host: str = "localhost"
    clang_worker_port: int = 50051
    clang_worker_timeout_seconds: float = 3.0
    clang_worker_parse_timeout_seconds: float = 120.0

    artifact_storage_path: str = "/app/data/artifacts"
    toolchain_profile_dir: str = "/app/shared/toolchain_profiles"

    rule_engine_tu_workers: int = 2
    rule_engine_rule_workers: int = 4
    rule_engine_timeout_seconds: float = 5.0
    rule_engine_enabled: bool = True

    rate_limit_requests: int = 200
    rate_limit_window_seconds: int = 60

    auth_required: bool = False
    oidc_enabled: bool = False
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_uri: str = ""
    oidc_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    api_keys: list[str] = Field(default_factory=list)

    prometheus_enabled: bool = True
    otel_enabled: bool = False
    otel_service_name: str = "misra-compliance-platform"
    otel_exporter_endpoint: str = "http://localhost:4317"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def clang_worker_address(self) -> str:
        return f"{self.clang_worker_host}:{self.clang_worker_port}"

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()
