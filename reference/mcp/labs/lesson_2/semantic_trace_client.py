import sys

from typing import Any
from collections.abc import Awaitable
from datetime import datetime, timezone


def _log(direction: str, method: str, item) -> None:
    """Logging errors must never interrupt message delivery."""

    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    print(f"\n\n[^^^^^^ SEMANTIC | CLIENT-{direction}: [{method}] *******]\n"
          f"\n{timestamp}"
          f"\n{item}",
          file=sys.stderr, flush=True)


async def trace_client(
        method: str,
        params: dict[str, Any],
        operation: Awaitable[Any],
) -> Any:
    # [1] CLIENT OUT TRACE
    _log("OUT", method, f"[params]: {params!r}")

    try:
        # forward the original message unchanged
        result = await operation
    except Exception as exc:

        # CLIENT ERROR TRACE
        _log("ERROR", method, f"[exception]: {exc!r}")
        print("\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
              file=sys.stderr,
              flush=True)
        raise

    # [4] CLIENT IN TRACE
    _log("IN", method, f"[result]: {result!r}")

    return result
