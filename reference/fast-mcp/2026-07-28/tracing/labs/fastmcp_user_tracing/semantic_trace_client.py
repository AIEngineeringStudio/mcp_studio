"""Your semantic client tracer, now grouped into the shared JSONL trace store."""
from __future__ import annotations

import os
import sys
from collections.abc import Awaitable
from datetime import datetime, timezone
from typing import Any

from trace_store import current_session, emit, new_id, redact


def _log(direction: str, method: str, item: Any,
         operation_id: str, *, tool_name: str | None = None) -> None:
    # Keep the original human-readable trace when explicitly requested.
    # It contains application values; do not enable with sensitive data.
    if os.environ.get("MCP_TRACE_CONSOLE") == "1":
        try:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            print(f"\n[^^^^^^ SEMANTIC | CLIENT-{direction}: [{method}]]\n"
                  f"{timestamp}\n{redact(item)!r}", file=sys.stderr, flush=True)
        except Exception:
            pass

    emit("CLIENT", direction=("OUT" if direction == "OUT" else
                              "IN" if direction == "IN" else "ERROR"),
         transport="semantic", event=("semantic_call" if direction == "OUT" else
                                       "semantic_result" if direction == "IN" else
                                       "semantic_error"),
         trace_session_id=current_session(),
         rpc_method=method, tool_name=tool_name,
         semantic_operation_id=operation_id,
         detail=None if direction != "ERROR" else str(type(item).__name__))


async def trace_client(method: str, params: dict[str, Any],
                       operation: Awaitable[Any]) -> Any:
    """Preserve your original wrapper: return exactly what the operation returns."""
    op_id = new_id()
    tool_name = params.get("name") if isinstance(params.get("name"), str) else None
    _log("OUT", method, params, op_id, tool_name=tool_name)
    try:
        result = await operation
    except Exception as exc:
        _log("ERROR", method, exc, op_id, tool_name=tool_name)
        raise
    _log("IN", method, result, op_id, tool_name=tool_name)
    return result
