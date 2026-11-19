"""Structured logging configured safely for MCP stdio servers."""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog
from opentelemetry import trace

from mcp_lab.observability.config import Settings


def _add_trace_context(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        event_dict["trace_id"] = format(context.trace_id, "032x")
        event_dict["span_id"] = format(context.span_id, "016x")
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configure all logs on stderr because stdout may carry MCP traffic."""

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )
    logging.basicConfig(stream=sys.stderr, level=level, format="%(message)s", force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_trace_context,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.PositionalArgumentsFormatter(),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "mcp_lab") -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
