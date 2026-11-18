# MCP Server with Streamable HTTP Transport

## Chunk 5 of 8 — §06. Progress and Elicitation

**Version boundary:**

> This chapter targets MCP `2025-11-25`. In that revision, elicitation is a
> server-to-client `elicitation/create` request sent during an initialized
> session. Do not replace it with the later multi-round-trip pattern.

**Learning outcome:**

> Add form-mode elicitation to a long-running tool while preserving the
> distinction among progress, user input, final results, and business state.

## §06. The Intermediate Requirement

The basic tool processed a fixed number of records. The new requirement is:

1. Process the first batch.
2. Ask the user whether to continue and what batch size to use.
3. Respect `accept`, `decline`, and `cancel`.
4. Continue reporting progress.
5. Return one final result.

```text
tools/call
    |
    +--- progress: first batch completed
    +--- elicitation/create: continue and batch size?
    +--- client response: accept, decline, or cancel
    +--- progress: remaining records completed
    |
    +--- one final CallToolResult
```

The elicitation answer is input to the operation. It is not an authorization
decision by itself. A production service must separately authenticate the
caller and authorize the requested action.

## Extend the Basic Exercise

Continue using the project and exact dependency from chunk 4:

```text
mcp[cli]==1.29.1
```

Replace `server.py` and `client.py` with the following versions.

### `server.py`

```python
import asyncio

from pydantic import BaseModel, Field

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession


mcp = FastMCP("Interactive batch server")


class BatchChoice(BaseModel):
    continue_processing: bool = Field(
        description="Continue processing the remaining records"
    )
    batch_size: int = Field(
        ge=1,
        le=20,
        description="Number of records to process per batch",
    )


@mcp.tool()
async def process_records(
    total: int,
    initial_batch_size: int,
    ctx: Context[ServerSession, None],
) -> dict[str, int | str]:
    """Process records, asking once after the first batch."""
    if total < 1 or total > 100:
        raise ValueError("total must be between 1 and 100")
    if initial_batch_size < 1 or initial_batch_size > 20:
        raise ValueError("initial_batch_size must be between 1 and 20")

    processed = 0
    batch_size = initial_batch_size
    asked = False

    while processed < total:
        current_batch = min(batch_size, total - processed)
        await asyncio.sleep(0.05)
        processed += current_batch

        await ctx.report_progress(
            progress=processed,
            total=total,
            message=f"Processed {processed} of {total}",
        )

        if processed < total and not asked:
            asked = True
            result = await ctx.elicit(
                message=(
                    f"Processed {processed} of {total}. "
                    "Continue with another batch?"
                ),
                schema=BatchChoice,
            )

            if result.action == "decline":
                return {"status": "declined", "processed": processed}
            if result.action == "cancel":
                return {"status": "cancelled", "processed": processed}
            if result.data is None:
                return {"status": "no_input", "processed": processed}
            if not result.data.continue_processing:
                return {"status": "stopped", "processed": processed}

            batch_size = result.data.batch_size

    return {"status": "completed", "processed": processed}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

The tool awaits a standard MCP elicitation response. The SDK may suspend this
Python coroutine internally, but a suspended coroutine is not part of the wire
protocol and should not be used as durable business state.

### `client.py`

```python
import asyncio
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.context import RequestContext


async def handle_elicitation(
    context: RequestContext[ClientSession, Any],
    params: types.ElicitRequestParams,
) -> types.ElicitResult | types.ErrorData:
    del context

    if isinstance(params, types.ElicitRequestURLParams):
        print(f"URL requested: {params.url}")
        return types.ElicitResult(action="decline")

    print(f"question: {params.message}")
    print(f"schema: {params.requestedSchema}")

    # Deterministic test response. A real host must render a user-facing form
    # and return the user's actual choice.
    return types.ElicitResult(
        action="accept",
        content={
            "continue_processing": True,
            "batch_size": 3,
        },
    )


async def show_progress(
    progress: float,
    total: float | None,
    message: str | None,
) -> None:
    print(f"progress: {progress}/{total} — {message or ''}")


async def main() -> None:
    endpoint = "http://127.0.0.1:8000/mcp"

    async with streamable_http_client(endpoint) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
            elicitation_callback=handle_elicitation,
        ) as session:
            initialized = await session.initialize()
            print(f"protocol: {initialized.protocolVersion}")

            result = await session.call_tool(
                "process_records",
                arguments={"total": 8, "initial_batch_size": 2},
                progress_callback=show_progress,
            )

            if result.isError:
                raise RuntimeError("tool reported an error")

            print(f"final result: {result.structuredContent}")


if __name__ == "__main__":
    asyncio.run(main())
```

Registering the elicitation callback causes this SDK client to advertise
elicitation support during initialization. A client without the capability must
not receive `elicitation/create` requests.

## Run the Exercise

Start the server in terminal 1:

```bash
uv run python server.py
```

Run the client in terminal 2:

```bash
uv run python client.py
```

The important order is:

```text
protocol: 2025-11-25
progress: 2.0/8.0 — Processed 2 of 8
question: Processed 2 of 8. Continue with another batch?
schema: ...
progress: 5.0/8.0 — Processed 5 of 8
progress: 8.0/8.0 — Processed 8 of 8
final result: {'status': 'completed', 'processed': 8}
```

## Wire-Level Interpretation

```text
Client                                                Server
  |--- tools/call, progressToken ---------------------->|
  |<== notifications/progress: 2/8 ====================|
  |<== elicitation/create request =====================|
  |                                                     |
  |    host obtains the user's actual decision          |
  |                                                     |
  |--- ElicitResult response in a new POST ------------>|
  |<== notifications/progress: 5/8 ====================|
  |<== notifications/progress: 8/8 ====================|
  |<== final tools/call response =======================|
```

The transport routes the elicitation response by its JSON-RPC request ID. An
application must not invent a second `/elicit/{session_id}` endpoint or treat
the session ID as the elicitation correlation ID.

## Handle Every Response Action

**Accept:**

> The user submitted form content. Validate it against the requested schema and
> then apply normal business validation and authorization.

**Decline:**

> The user explicitly rejected the request. The tool should stop or use a safe,
> documented alternative.

**Cancel:**

> The interaction was dismissed without an explicit yes or no. Do not silently
> reinterpret cancellation as acceptance.

The server must also handle a client that does not support elicitation or
disconnects while the request is outstanding.

## Form Mode and URL Mode

Form mode is for non-sensitive structured input such as a quantity, date, or
selection. Its schema intentionally supports a restricted set of JSON Schema
features so clients can render predictable forms.

URL mode is for out-of-band interactions involving sensitive data, credentials,
payments, or third-party authorization:

```text
Server -- elicitation/create with mode=url --> Client
Client -- shows domain and asks permission ------> User
User ---- completes interaction in browser ------> External service
Server -- notifications/elicitation/complete ---> Client, optionally
```

The client returns `action: accept` to indicate consent to open the URL. It does
not return the secret or prove that the out-of-band workflow completed.

Form mode must not request passwords, API keys, access tokens, or payment
credentials.

## State Boundaries

Three types of state are easy to confuse:

**Transport session state:**

> Version, capabilities, outstanding JSON-RPC requests, and optional
> `MCP-Session-Id` routing.

**Continuation state:**

> Information required to continue the in-flight operation after the user
> answers, such as `processed`, `total`, and the pending question.

**Durable business state:**

> Committed records, audit events, authorization decisions, and idempotency
> keys that must survive process or session loss.

The sample keeps continuation state in one Python coroutine because it is a
local concept exercise. A production design must decide what happens if the
process restarts while the user is answering. Protocol session state alone is
not a durable recovery design.

## Safe Side-Effect Ordering

For operations that modify data:

1. Gather required user input.
2. Authenticate and authorize the caller.
3. Validate the input against current business state.
4. Perform the write transaction.
5. Record an idempotency key or operation ID.
6. Return the final result.

Do not perform an irreversible write and then elicit approval for that same
write.

## Failure Scenarios

**Client lacks elicitation capability:**

> Return a clear unsupported-feature error or offer a documented tool argument.
> Never assume approval.

**User never responds:**

> Apply a bounded timeout and cancel or fail safely. Do not keep an unlimited
> number of suspended operations.

**Connection breaks after the answer:**

> The client may not know whether the server completed the operation. Use an
> application operation ID and status lookup before retrying a side effect.

**Server restarts mid-call:**

> The optional session may be lost. A new initialization does not automatically
> recover the business operation.

## Summary

- Elicitation uses the standard `elicitation/create` request.
- The client must advertise the corresponding capability.
- The response is `accept`, `decline`, or `cancel`.
- Form mode is for non-sensitive structured data.
- URL mode keeps sensitive interaction data outside the MCP client.
- Progress, elicitation, and the final result are separate messages.
- Session state, continuation state, and durable business state are different.
- A deterministic callback is appropriate for a test, not a substitute for
  actual user consent.

**Professional articulation:**

> “In MCP `2025-11-25`, the server can issue `elicitation/create` during a tool
> call after the client advertises support. The client obtains the user's input
> and posts a normal JSON-RPC response; the tool still finishes with one final
> result.”

## Sources

- [MCP `2025-11-25`: Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [MCP `2025-11-25`: Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Official Python SDK v1: Building servers](https://py.sdk.modelcontextprotocol.io/v1/server/)
- [Official Python SDK v1 client session source](https://github.com/modelcontextprotocol/python-sdk/blob/v1.x/src/mcp/client/session.py)

## Next

Continue with [chunk 6: production concerns](chunk-6.md).
