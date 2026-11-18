# The first client and in-memory testing

**Outcome:** Run a deterministic MCP interaction without an LLM or a network service.

**Prerequisites:** [04: Protocol versions and capability discovery](04-versions-discovery.md), [06: FastMCP registration and dispatch](06-fastmcp-registry.md).

## Remove boundaries until the contract is visible

Before introducing a subprocess, HTTP, credentials, or a model, verify that
client and server agree about one operation. The in-memory client supplies
this small test boundary.

```
One Python process
+------------------------------------------------+
| Client --> MCP dispatch --> get_ticket --> data |
+------------------------------------------------+
```

This still exercises a framework/protocol path. It is different from calling
`lookup_ticket` directly, but it does not prove network connectivity.

## Run the supplied files

Follow [lab setup](../labs/README.md), then run from the lab directory:

```bash
uv run python client.py memory
```

Read [client.py](../labs/client.py) beside [server.py](../labs/server.py).
The client enters `async with Client(mcp)`, lists tools, calls
`get_ticket`, reads a ticket resource, and obtains a prompt.

Expected output:

```
memory: tool, resource, and prompt checks passed
```

The assertion after the tool call checks that ticket T-100 is open. The resource
assertion checks readable content. The prompt assertion checks that the
parameterized instructions reference the requested ticket. They verify
observable behavior instead of merely checking that no exception occurred.

## Why asynchronous code appears

A client operation may wait for work to finish. `await` lets the current
coroutine pause while other work can proceed. `asyncio.run` starts the event
loop for this small program. The context manager scopes connection and cleanup.

At this stage, understanding every event-loop detail is unnecessary. The
important lifetime is “enter client, perform operations, leave client.”
A later guide explains concurrency and cancellation.

## What the result proves

A passing test shows that these registered components can be discovered and
invoked through this client/library combination. It does not prove:

- a child process can find the same interpreter and source files;
- a remote endpoint is reachable or authenticated;
- an AI host can select the tool or render every optional capability.

Those require additional boundaries and checks.

## A useful failure experiment

Temporarily call the tool with a nonexistent ticket ID and observe the error.
Then restore the valid input. Compare that with using a nonexistent tool name.
The former reaches application behavior; the latter fails before the intended
handler can run.

The lab includes only synthetic records. No provider credentials or paid model
calls are needed. This keeps the failure signal about MCP contracts.

**Professional articulation:**

> “The in-memory test validates component contracts before we add process and
> network failure modes.”

## Sources and next step

- [Archive: conversations/chatgpt/1_FirstMCPTool_InProcess.md](../../conversations/chatgpt/1_FirstMCPTool_InProcess.md)
- [Archive: _learning_resources/mcp_notes2.md](../../_learning_resources/mcp_notes2.md)
- [Official reference](https://gofastmcp.com/docs/clients/client) — checked 2026-11-15.

Next: [stdio and subprocess boundaries](08-stdio-processes.md).

