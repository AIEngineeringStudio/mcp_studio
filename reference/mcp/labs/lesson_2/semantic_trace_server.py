import sys
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
from datetime import datetime, timezone


def _log(direction: str, method: str, item) -> None:
    """Logging errors must never interrupt message delivery."""

    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    print(f"\n\n[^^^^^^ SEMANTIC | SERVER-{direction}: [{method}] *******]\n"
          f"\n{timestamp}"
          f"\n{item}",
          file=sys.stderr, flush=True)


class SemanticTrace(Middleware):
    """ Covers `inbound requests` and `notifications`
    at the server middleware layer """

    async def on_message(
            self,
            context: MiddlewareContext,
            call_next: CallNext[Any, Any]
    ):
        timestamp = datetime.now(timezone.utc).isoformat(
            timespec="milliseconds")
        method = context.method

        # [2] SERVER IN TRACE
        _log("IN", method, f"[{method}]: {context.message!r}")

        # In Python, !r means use repr() inside an f-string.
        # It displays the developer representation of a value instead of its
        # normal string representation.
        # message = "Hello\nWorld"
        #
        # print(f"{message}")     # Uses str()
        # print(f"{message!r}")   # Uses repr()
        #
        # With !r:    Prints 'Hello\nWorld'.
        # Without !r: Prints world in next line

        try:
            # forward the original message unchanged
            result = await call_next(context)
        except Exception as exc:

            # SERVER ERROR TRACE
            _log("ERROR", method, f"[{method}]: {exc!r}")
            print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",
                  file=sys.stderr,
                  flush=True)
            raise

        # [3] SERVER OUT TRACE
        _log("OUT", method, f"[{method}]: {result!r}")

        return result
