# Lesson 7 — Elicitation through multi-round requests

## Outcome

After this lesson, you can trace an elicitation request, distinguish
`input_required` from a final result, and design retry-safe continuation state.

## Why elicitation exists

A tool sometimes need user's input after it starts. The server must not invent
the user's answer.

```
call operation
     |
     +-- enough input --> complete
     |
     +-- input_required -> client asks user -> retry
```

MCP `2026-07-28` uses Multi Round-Trip Requests (MRTR). The server returns the
question as data instead of sending a nested JSON-RPC request to the client.

## MCP Tool - `bidirectional_batch`

**MRTR execution model:**

The server returns its continuation state. The client sends it back with the
answer in the next request.

FastMCP officially supports the guard pattern for MRTR.

| Legacy API               | Modern API                   |
|--------------------------|------------------------------|
| await `ctx.elicit()`     | Return `InputRequiredResult` |
| Suspended coroutine      | Fresh function invocation    |
| Local variables retained | `ctx.request_state`          |
| Awaited client answer    | `ctx.input_responses`        |

### Execution flow

```
CLIENT                              SERVER
   |                                   |
   |--- tools/call (batch_size=4) ---->| Tool invocation #1
   |                                   | 
   |<-- Progress 1                     | Process 4 rows
   |<-- Progress 2                     |
   |<-- Progress 3                     |
   |<-- Progress 4                     |
   |<-- InputRequiredResult -----------| Return InputRequiredResult
   |                                   |   
   |                                   | Invocation ends
   |
   | User enters 3
   |
   |--- tools/call + response -------->| Tool invocation #2
   |     + requestState                | 
   |                                   | Restore state + 
   |                                   | Read input_responses
   |                                   |    
   |<-- Progress 5                     | Process 3 rows
   |<-- Progress 6                     |
   |<-- Progress 7                     |
   |<-- InputRequiredResult -----------|
   |                                   | Invocation ends
   |
   | User enters 0
   |
   |--- tools/call + response -------->| Tool invocation #3
   |    + requestState                 | Restore state + 
   |                                   | Read input_responses
   |                                   |   
   |<-- Total rows processed: 7 -------| Return final result
```

### Important APIs

| API                       | Purpose                                        |
|---------------------------|------------------------------------------------|
| `ctx.report_progress()`   | Send SSE progress notifications                |
| `ctx.request_state`       | Restore previous execution state               |
| `ctx.input_responses`     | Read client elicitation answers                |
| `ElicitRequest`           | Define the question                            |
| `ElicitRequestFormParams` | Define the expected answer schema              |
| `InputRequiredResult`     | Complete the current round and request another |
| `return str`              | Complete the logical tool call                 |

### Key Points

| API                         | Responsibility                               |
|-----------------------------|----------------------------------------------|
| `mode="auto"`               | Discover the supported protocol              |
| `client.protocol_version`   | Verify the negotiated version                |
| `progress_handler`          | Receive progress notifications               |
| `elicitation_handler`       | Answer server questions                      |
| `input_required_max_rounds` | Prevent unlimited MRTR rounds                |
| `client.call_tool()`        | Manage the complete tool execution lifecycle |

**FastMCP automatically handles the MRTR continuation requests.** The
application does not need to manage `requestState` or `inputResponses` manually.

**Why use mode="auto"?**

There are two relevant options.

| Option            | Behavior                               |
|-------------------|----------------------------------------|
| mode="auto"       | Discover the server's protocol version |
| mode="2026-07-28" | Pin the version without discovery      |

I selected automatic discovery followed by an explicit version check.
This verifies compatibility rather than simply assuming it.

## Round 1: server requests input

The repeated request `_meta` is omitted here for readability.

```http request
POST /mcp
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: bidirectional_batch
Content-Type: application/json
Accept: application/json, text/event-stream
```

```json
{
  "jsonrpc": "2.0",
  "id": 101,
  "method": "tools/call",
  "params": {
    "name": "bidirectional_batch",
    "arguments": {
      "initial_batch_size": 4
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "elicitation": {
          "form": {}
        }
      },
      "progressToken": "progress-101"
    }
  }
}
```

### Response — Input required

The server streams progress notifications and then returns a result similar to:

```json
{
  "jsonrpc": "2.0",
  "id": 101,
  "result": {
    "resultType": "input_required",
    "requestState": "<opaque-protected-token>",
    "inputRequests": {
      "batch_1": {
        "method": "elicitation/create",
        "params": {
          "message": "Processed 4 rows. Continue?",
          "requestedSchema": {
            "type": "object",
            "properties": {
              "batch_size": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10
              }
            },
            "required": [
              "batch_size"
            ]
          }
        }
      }
    }
  }
}
```

## Round 2: client retries the original request

The retry uses a new JSON-RPC ID because it is a new request:

```json
{
  "jsonrpc": "2.0",
  "id": 102,
  "method": "tools/call",
  "params": {
    "name": "bidirectional_batch",
    "arguments": {
      "initial_batch_size": 4
    },
    "requestState": "<opaque-protected-token>",
    "inputResponses": {
      "batch_1": {
        "action": "accept",
        "content": {
          "batch_size": 3
        }
      }
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "elicitation": {
          "form": {}
        }
      },
      "progressToken": "progress-102"
    }
  }
}
```

The terminal response uses `resultType: "complete"`.

Notice that the original tool arguments remain unchanged.
The elicitation answer travels separately in `inputResponses`.

The SDK handles this entire exchange automatically.

## Guard-pattern implementation model

```
start operation
  |
  +-- no response ------> return InputRequiredResult
  |
  +-- decline/cancel ---> return a safe terminal result
  |
  +-- accept -----------> re-authorize, apply once, return complete
```

The server may receive the operation more than once. Put side effects after the
guard, make them idempotent, and store a server-controlled operation key when
exactly-once business behavior matters.

`requestState` is opaque to the client, but the client transports it. Protect
its integrity and bind it to identity, operation, and expiry. Do not put
secrets or large application objects in it.

## Form mode and URL mode

Use form mode for non-secret structured input. Avoid requesting passwords,
private keys, or raw access tokens in a model-visible form.

URL mode sends the user to an external interaction. It is not a replacement for
MCP OAuth, and the return path still needs correlation, expiry, and replay
protection.

## Requests allowed to use MRTR

Only these core requests may return `InputRequiredResult`:

- `tools/call`;
- `resources/read`;
- `prompts/get`.

Other methods must not return this result type.

## Failure and Recovery

Consider the server restarting after processing the first four rows.

```
POST #1
   |
Process 4 rows
   |
Return protected requestState
   |
SERVER RESTARTS
   |
POST #2 with previous requestState
   |
State verification fails
```

The current server generates a new encryption key at startup. After a restart,
it cannot verify continuation tokens created using the previous key.

For this local demonstration, the client must restart the operation.

For production, use a persistent shared secret for continuation-state
protection and durable, idempotent batch processing. Otherwise, retrying a
request could process the same rows twice.

## Hands-on checkpoint

### Project structure**

```
mcp-elicitation/
├── pyproject.toml
├── server.py
├── client.py
└── tools/
    ├── __init__.py
    └── bidirectional_batch.py
```

### **pyproject.toml**

```toml
[project]
name = "mcp-elicitation"
version = "0.1.0"
description = "Small, synthetic examples for mcp-elicitation"
requires-python = ">=3.14,<3.15"

dependencies = [
    "fastmcp==4.2.0",
]

[tool.uv]
package = false
```

### MCP Tool

**tools/__init__.py**

```python
from .bidirectional_batch import bidirectional_batch
```

**tools/bidirectional_batch.py**

```python
import asyncio
import json

from fastmcp import Context

from mcp.types import (
    InputRequiredResult,
    ElicitRequest,
    ElicitRequestFormParams,
    ElicitResult,
)


async def bidirectional_batch(
        initial_batch_size: int,
        ctx: Context,
) -> str | InputRequiredResult:
    """Process batches with progress streaming and elicitation."""

    # 1. Verify protocol version

    if ctx.request_context.protocol_version != "2026-07-28":
        raise ValueError("MCP 2026-07-28 is required.")

    # 2. Initial invocation

    if ctx.request_state is None:

        batch_size = max(1, min(initial_batch_size, 10))
        total_processed = 0
        batch_number = 0

    # 3. Continuation invocation

    else:

        state = json.loads(ctx.request_state)

        total_processed = state["total_processed"]
        batch_number = state["batch_number"]

        responses = ctx.input_responses or {}
        answer = responses.get("next_batch")

        if not isinstance(answer, ElicitResult):
            raise ValueError("Missing elicitation response.")

        if answer.action != "accept":
            return f"Stopped. Total rows processed: {total_processed}"

        batch_size = (answer.content or {}).get("batch_size")

        if type(batch_size) is not int or not 0 <= batch_size <= 10:
            raise ValueError("Batch size must be between 0 and 10.")

        if batch_size == 0:
            return f"Total rows processed: {total_processed}"

    # 4. Process one batch

    batch_number += 1

    for row in range(1, batch_size + 1):
        await asyncio.sleep(0.2)

        total_processed += 1

        await ctx.report_progress(
            progress=total_processed,
            total=None,
            message=(
                f"server update: processed "
                f"batch {batch_number}, "
                f"row {row}/{batch_size}, "
                f"total={total_processed}"
            ),
        )

    # 5. Construct elicitation request

    elicitation = ElicitRequest(
        method="elicitation/create",
        params=ElicitRequestFormParams(
            message=(
                f"Processed {total_processed} rows. "
                "Enter the next batch size (1-10), "
                "or 0 to stop."
            ),
            requested_schema={
                "type": "object",
                "properties": {
                    "batch_size": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                    }
                },
                "required": ["batch_size"],
            },
        ),
    )

    # 6. Preserve execution state

    state = json.dumps({
        "total_processed": total_processed,
        "batch_number": batch_number,
    })

    # 7. Return intermediate result

    return InputRequiredResult(
        result_type="input_required",
        input_requests={
            "next_batch": elicitation,
        },
        request_state=state,
    )

```

### MCP server

**server.py**

```python
import argparse

from fastmcp import FastMCP
from tools import bidirectional_batch

mcp = FastMCP("Elicitation-exercise")

# Register tools
mcp.tool(bidirectional_batch)

if __name__ == "__main__":
    choices = ["stdio", "http"]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=choices,
        required=True,
        # default="stdio",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=8000,
            path="/mcp",
        )

```

### MCP Client

**client.py**

```python
"""Verify MRTR elicitation using MCP 2026-07-28."""

import argparse
import asyncio
import sys

from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult

from fastmcp.client.transports import (
    StdioTransport,
    StreamableHttpTransport,
)


SERVER_URL = "http://127.0.0.1:8000/mcp"
PROTOCOL_VERSION = "2026-07-28"


# ── Transport selection ──────────────────────────

def client_source(mode: str) -> Any:

    if mode == "in-memory":
        from server import mcp

        return mcp

    if mode == "stdio":
        return StdioTransport(
            command=sys.executable,
            args=[
                str(
                    Path(__file__).resolve()
                    .with_name("server.py")
                ),
                "--transport",
                "stdio",
            ],
            keep_alive=False,
        )

    if mode == "http":
        return StreamableHttpTransport(
            url=SERVER_URL,
        )

    raise ValueError(f"Unsupported mode: {mode}")


# ── Progress handler ────────────────────────────

async def progress_handler(
    progress: float,
    total: float | None,
    message: str | None,
) -> None:

    print(f"[PROGRESS] {message}", flush=True)


# ── Elicitation handler ─────────────────────────

async def elicitation_handler(
    message,
    response_type,
    params,
    context,
):

    print(f"\n[ELICIT] {message}")

    while True:
        try:
            batch_size = int(
                await asyncio.to_thread(
                    input,
                    "Enter batch size (0-10): ",
                )
            )

            if 0 <= batch_size <= 10:
                break

        except ValueError:
            pass

        print("Enter an integer between 0 and 10.")

    print(f"[REPLY] batch_size={batch_size}")

    return ElicitResult(
        action="accept",
        content=response_type(
            batch_size=batch_size
        ),
    )


# ── Tool invocation ─────────────────────────────

async def run_elicitation_example(
    client: Client,
) -> None:

    result = await client.call_tool(
        "bidirectional_batch",
        arguments={
            "initial_batch_size": 4,
        },
    )

    print(f"\n[RESULT] {result.content[0].text}")


# ── Main ────────────────────────────────────────

async def main(
    transport_name: str,
    example_name: str,
) -> None:

    async with Client(
        transport=client_source(transport_name),
        name=f"verify-{example_name}-client",
        mode="auto",
        init_timeout=10,
        progress_handler=progress_handler,
        elicitation_handler=elicitation_handler,
    ) as client:

        print(f"Transport: {transport_name}")

        if client.protocol_version != PROTOCOL_VERSION:
            raise RuntimeError(
                f"Expected {PROTOCOL_VERSION}, "
                f"received {client.protocol_version}"
            )

        print(f"Protocol: {client.protocol_version}")

        for tool in await client.list_tools():
            print(f"[TOOL] {tool.name}")

        if example_name == "elicitation":
            await run_elicitation_example(client)

        else:
            raise ValueError(
                f"Unsupported example: {example_name}"
            )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--transport",
        choices=["in-memory", "stdio", "http"],
        required=True,
    )

    parser.add_argument(
        "--example",
        choices=["elicitation"],
        required=True,
    )

    args = parser.parse_args()

    asyncio.run(
        main(args.transport, args.example)
    )
```

## **8. Run locally**

Run the focused progress and cancellation exercise from [labs](labs):

### Install dependencies:

```shell
uv sync
```

### Option 1: `in-memory` transport

#### Run `progress` example

```shell
uv run python client.py --transport in-memory --example elicitation
```

#### Run `cancel` example

```shell
uv run python client.py --transport in-memory --example cancel
```

### Option 2: `stdio` transport

#### Run `progress` example

```shell
uv run python client.py --transport stdio --example elicitation
```

#### Run `cancel` example

```shell
uv run python client.py --transport stdio --example cancel
```

### Option 3: `http` transport

#### Run `progress` example

**Terminal 1 — Start the server**

```shell
uv run server.py --transport http 
```

**Terminal 2 — Start the client**

```shell
uv run pythonclient.py --transport http --example elicitation
```


**Expected output:**

```
Transport: stdio
Protocol: 2026-07-28
[TOOL] bidirectional_batch
[PROGRESS] server update: processed batch 1, row 1/4, total=1
[PROGRESS] server update: processed batch 1, row 2/4, total=2
[PROGRESS] server update: processed batch 1, row 3/4, total=3
[PROGRESS] server update: processed batch 1, row 4/4, total=4

[ELICIT] Processed 4 rows. Enter the next batch size (1-10), or 0 to stop.
Enter batch size (0-10): 3
[REPLY] batch_size=3
[PROGRESS] server update: processed batch 2, row 1/4, total=5
[PROGRESS] server update: processed batch 2, row 2/4, total=6
[PROGRESS] server update: processed batch 2, row 3/4, total=7

[ELICIT] Processed 7 rows. Enter the next batch size (1-10), or 0 to stop.
Enter batch size (0-10): 0
[REPLY] batch_size=0

[RESULT] Total rows processed: 7

```

Read the complete runnable state machine in
[`continuation_model.py`](../labs/continuation_model.py). It deliberately tests
the application behavior below MRTR; it does not pretend to be a user interface
or a raw MCP wire implementation.

Then read
[`../concepts/13-elicitation.md`](../../../concepts/13-elicitation.md) and
[
`../concepts/14-continuation-state.md`](../../../concepts/14-continuation-state.md).

**Say it professionally:**

> Modern elicitation is a multi-round state machine. The server returns an
> `input_required` result, the client gathers input, and the client retries the
> original operation with a new request ID and explicit continuation data.

## Official references

- [MRTR](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)
- [FastMCP elicitation](https://gofastmcp.com/servers/elicitation)

