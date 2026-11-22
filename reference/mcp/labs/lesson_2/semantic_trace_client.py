import sys

from typing import Any
from collections.abc import Awaitable


async def trace_client(
        method: str,
        params: dict[str, Any],
        operation: Awaitable[Any],
) -> Any:
    # [1] CLIENT OUT TRACE
    print("\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
          file=sys.stderr,
          flush=True)

    print(
        f"[CLIENT OUT/CALL] {method}: {params!r}",
        file=sys.stderr,
        flush=True,
    )

    try:
        # forward the original message unchanged
        result = await operation
    except Exception as exc:
        print(
            f"[CLIENT ERROR] {method}: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        print("\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
              file=sys.stderr,
              flush=True)
        raise

    # [4] CLIENT IN TRACE
    print(
        f"[CLIENT IN/RESULT] {method}: {result!r}",
        file=sys.stderr,
        flush=True,
    )
    print("\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
          file=sys.stderr,
          flush=True)
    return result
