import sys
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext


class SemanticTrace(Middleware):
    """ Covers `inbound requests` and `notifications`
    at the server middleware layer """

    async def on_message(
            self,
            context: MiddlewareContext,
            call_next: CallNext[Any, Any]
    ):
        # [2] SERVER IN TRACE
        # Observe messages and log necessary details
        print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",
              file=sys.stderr,
              flush=True)
        print(
            f"\n[SERVER IN] {context.method}: {context.message!r}",
            # What is `context.source` ??
            file=sys.stderr,
            flush=True,
        )

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
            print(
                f"\n[SERVER ERROR] {context.method}: {exc!r}",
                file=sys.stderr,
                flush=True,
            )
            print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",
                  file=sys.stderr,
                  flush=True)
            raise

        # [3] SERVER OUT TRACE
        print(
            f"\n[SERVER DONE] {context.method}: {result!r}",
            file=sys.stderr,
            flush=True
        )
        print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",
              file=sys.stderr,
              flush=True)

        return result
