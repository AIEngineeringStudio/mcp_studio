"""Append-only JSON Lines recorder for raw and decoded protocol events."""

import json
import threading
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mcp_lab.wire.redaction import redact


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, BaseException):
        return {"type": type(value).__name__, "message": str(value)}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


class JsonlWireRecorder:
    """Thread-safe, append-only event recorder with recursive redaction."""

    def __init__(self, path: Path | str, *, enabled: bool = True) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self._lock = threading.Lock()

    def record(
        self,
        *,
        direction: str,
        vantage_point: str,
        transport: str,
        payload: Any,
        **fields: Any,
    ) -> None:
        if not self.enabled:
            return
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "direction": direction,
            "vantage_point": vantage_point,
            "transport": transport,
            "payload": redact(to_jsonable(payload)),
            **redact(to_jsonable(fields)),
        }
        encoded = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(encoded + "\n")

    def record_json_line(
        self,
        line: bytes,
        *,
        direction: str,
        vantage_point: str,
        transport: str,
        max_bytes: int,
    ) -> None:
        truncated = len(line) > max_bytes
        sample = line[:max_bytes]
        try:
            payload: Any = json.loads(sample.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {"raw": sample.decode("utf-8", errors="replace").rstrip("\r\n")}
        self.record(
            direction=direction,
            vantage_point=vantage_point,
            transport=transport,
            payload=payload,
            byte_length=len(line),
            truncated=truncated,
        )
