"""OpenTelemetry setup for application and MCP SDK spans."""

import threading

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from mcp_lab.observability.config import Settings

_lock = threading.Lock()
_configured = False


def configure_tracing(settings: Settings) -> None:
    """Install the global provider used automatically by the MCP SDK."""

    global _configured
    if not settings.tracing_enabled or settings.trace_exporter == "none":
        return
    with _lock:
        if _configured:
            return
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": settings.service_name,
                    "deployment.environment.name": settings.environment,
                }
            )
        )
        if settings.trace_exporter == "console":
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        else:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            except ImportError as exc:
                raise RuntimeError("OTLP tracing requires: uv sync --extra otlp") from exc
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint))
            )
        trace.set_tracer_provider(provider)
        _configured = True
