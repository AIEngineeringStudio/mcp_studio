"""Small JSONL trace store with a shared schema for HTTP and STDIO.

The trace IDs are application-owned diagnostics, not MCP protocol sessions.
Full payload recording is disabled by default: set MCP_TRACE_PAYLOAD=1 only for
synthetic/local data. Trace files are written with 0600 file permissions.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = 1
TRACE_SESSION_HEADER = "x-debug-trace-session"
HTTP_EXCHANGE_HEADER = "x-debug-http-exchange"
TRACE_SESSION_ENV = "MCP_TRACE_SESSION_ID"
STDIO_CONNECTION_ENV = "MCP_TRACE_STDIO_CONNECTION_ID"
# These IDs exist only in the tracer, never in the MCP protocol.
TRACE_SESSION_CONTEXT: ContextVar[str | None] = ContextVar("trace_session_id", default=None)
HTTP_EXCHANGE_CONTEXT: ContextVar[str | None] = ContextVar("http_exchange_id", default=None)


@contextmanager
def trace_scope(*, session: str | None, exchange: str | None = None):
    session_token = TRACE_SESSION_CONTEXT.set(valid_id(session))
    exchange_token = HTTP_EXCHANGE_CONTEXT.set(valid_id(exchange))
    try:
        yield
    finally:
        HTTP_EXCHANGE_CONTEXT.reset(exchange_token)
        TRACE_SESSION_CONTEXT.reset(session_token)


def current_session() -> str | None:
    return (TRACE_SESSION_CONTEXT.get()
            or valid_id(os.environ.get(TRACE_SESSION_ENV)))


def current_exchange() -> str | None:
    return HTTP_EXCHANGE_CONTEXT.get()


def current_stdio_connection() -> str | None:
    return valid_id(os.environ.get(STDIO_CONNECTION_ENV))


_HEX32 = re.compile(r"^[a-f0-9]{32}$")
_SECRET_KEYS = {"authorization", "cookie", "set-cookie", "password", "secret", "token",
                "access_token", "refresh_token", "client_secret", "api_key", "apikey"}


def new_id() -> str:
    return uuid4().hex


def valid_id(value: str | None) -> str | None:
    """Trace IDs are strictly lowercase UUID-hex strings, not trusted identity."""
    return value if value and _HEX32.fullmatch(value) else None


def redact(value: Any) -> Any:
    """Basic key-based redaction; not a general DLP or PII detector."""
    if isinstance(value, dict):
        return {str(k): ("[REDACTED]" if str(k).lower() in _SECRET_KEYS else redact(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def rpc_fields(envelope: Any) -> dict[str, Any]:
    """Extract protocol fields; notifications have rpc_id=None."""
    if not isinstance(envelope, dict):
        return {"rpc_id": None, "rpc_kind": "other", "rpc_method": None,
                "tool_name": None, "rpc_error_code": None}
    rpc_id = envelope.get("id")
    if "method" in envelope:
        kind = "request" if rpc_id is not None else "notification"
    elif "error" in envelope:
        kind = "error"
    elif "result" in envelope:
        kind = "response"
    else:
        kind = "other"
    params = envelope.get("params")
    tool_name = params.get("name") if isinstance(params, dict) else None
    return {"rpc_id": rpc_id, "rpc_kind": kind,
            "rpc_method": envelope.get("method"), "tool_name": tool_name,
            "rpc_error_code": (envelope["error"].get("code")
                               if isinstance(envelope.get("error"), dict) else None)}


class TraceStore:
    def __init__(self, side: str, directory: str | Path | None = None):
        if side not in ("CLIENT", "SERVER"):
            raise ValueError("side must be CLIENT or SERVER")
        self.side = side
        self.directory = Path(directory or os.environ.get("MCP_TRACE_DIR", "trace-logs")).resolve()
        self._lock = threading.Lock()
        self._fd: int | None = None
        self.path = self.directory / f"{side.lower()}-{os.getpid()}.jsonl"

    def _open(self) -> None:
        if self._fd is None:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)

    def close(self) -> None:
        with self._lock:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None

    def record(
        self, *, direction: str, transport: str, event: str,
        trace_session_id: str | None,
        http_exchange_id: str | None = None,
        stdio_connection_id: str | None = None,
        envelope: Any = None,
        http_method: str | None = None,
        path: str | None = None,
        http_status: int | None = None,
        detail: str | None = None,
        rpc_method: str | None = None,
        tool_name: str | None = None,
        semantic_operation_id: str | None = None,
    ) -> None:
        rpc = rpc_fields(envelope)
        if rpc_method is not None:
            rpc["rpc_method"] = rpc_method
        if tool_name is not None:
            rpc["tool_name"] = tool_name
        record = {
            "schema_version": SCHEMA_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "pid": os.getpid(),
            "side": self.side,
            "direction": direction,
            "transport": transport,
            "event": event,
            "trace_session_id": trace_session_id,
            "http_exchange_id": http_exchange_id,
            "stdio_connection_id": stdio_connection_id,
            "http_method": http_method,
            "path": path,
            "http_status": http_status,
            "detail": detail,
            "semantic_operation_id": semantic_operation_id,
            **rpc,
        }
        if envelope is not None and os.environ.get("MCP_TRACE_PAYLOAD") == "1":
            record["payload"] = redact(envelope)
        encoded = (json.dumps(record, default=str, separators=(",", ":"), ensure_ascii=False)
                   + "\n").encode("utf-8")
        # No shared logfile between client and server: separate role/PID files.
        # A lock keeps records from one process contiguous.
        with self._lock:
            self._open()
            assert self._fd is not None
            view = memoryview(encoded)
            while view:
                written = os.write(self._fd, view)
                if written == 0:
                    raise OSError("trace log write returned zero")
                view = view[written:]


_STORES: dict[str, TraceStore] = {}
_STORES_LOCK = threading.Lock()


def store_for(side: str) -> TraceStore:
    # Caches are process-local; never share an open file descriptor after fork.
    key = f"{side}-{os.getpid()}"
    with _STORES_LOCK:
        if key not in _STORES:
            _STORES[key] = TraceStore(side)
        return _STORES[key]


def emit(side: str, **fields: Any) -> None:
    """Best-effort entry point; tracingl must never break live MCP traffic."""
    try:
        store_for(side).record(**fields)
    except Exception as exc:
        # No recursive file logging when the log destination itself fails.
        try:
            import sys
            print(f"[mcp-trace] dropped record: {type(exc).__name__}",
                  file=sys.stderr, flush=True)
        except Exception:
            pass
