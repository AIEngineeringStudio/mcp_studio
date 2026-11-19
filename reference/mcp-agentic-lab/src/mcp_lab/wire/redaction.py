"""Conservative recursive redaction for diagnostic records."""

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(
    r"(^|[_-])(authorization|api[_-]?key|password|passwd|secret|token|cookie)([_-]|$)",
    re.IGNORECASE,
)


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _SECRET_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    return value
