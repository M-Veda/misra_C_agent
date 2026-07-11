"""OpenTelemetry distributed tracing setup."""

from __future__ import annotations

from fastapi import FastAPI

from misra_platform.core.config import Settings
from misra_platform.core.logging import get_logger

logger = get_logger(__name__)


def configure_tracing(app: FastAPI, settings: Settings) -> None:
    if not settings.otel_enabled:
        logger.info("otel_tracing_disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as error:
        logger.warning("otel_dependencies_missing", error=str(error))
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.version,
            "deployment.environment": settings.environment.value,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="/metrics,/api/v1/health,/api/v1/health/ready")
    HTTPXClientInstrumentor().instrument()
    logger.info(
        "otel_tracing_enabled",
        endpoint=settings.otel_exporter_endpoint,
        service=settings.otel_service_name,
    )
