"""Your server on_message middleware with structured semantic logging."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
from trace_store import (current_session, current_exchange,
                         current_stdio_connection, emit, redact)


def _log(direction: str, method: str, item: Any) -> None:
    if os.environ.get("MCP_TRACE_CONSOLE") == "1":
        try:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            print(f"\n[^^^^^^ SEMANTIC | SERVER-{direction}: [{method}]]\n"
                  f"{timestamp}\n{redact(item)!r}", file=sys.stderr, flush=True)
        except Exception:
            pass
    emit("SERVER", direction=("IN" if direction == "IN" else
                              "OUT" if direction == "OUT" else "ERROR"),
         transport="semantic", event=("semantic_in" if direction == "IN" else
                                       "semantic_out" if direction == "OUT" else
                                       "semantic_error"),
         trace_session_id=current_session(),
         http_exchange_id=current_exchange(),
         stdio_connection_id=current_stdio_connection(),
         rpc_method=method,
         detail=type(item).__name__ if direction == "ERROR" else None)


class SemanticTrace(Middleware):
    """Covers inbound requests/notifications; never changes their execution."""

    async def on_message(self, context: MiddlewareContext,
                         call_next: CallNext[Any, Any]):
        method = context.method
        _log("IN", method, context.message)
        try:
            result = await call_next(context)
        except Exception as exc:
            _log("ERROR", method, exc)
            raise
        _log("OUT", method, result)
        return result
