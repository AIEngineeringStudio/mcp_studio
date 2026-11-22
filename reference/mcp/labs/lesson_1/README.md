# **FastMCP 4.2 — Combined MCP Transport Inspection**

## **1. Transport comparison**

| Aspect               | In-memory                      | STDIO                      | Streamable HTTP                   |
|----------------------|--------------------------------|----------------------------|-----------------------------------|
| Server startup       | Implicit (Same Python process) | Client launches subprocess | Independently running HTTP server |
| Client connection    | `Client(mcp)`                  | `StdioTransport`           | `StreamableHttpTransport`         |
| Network required     | No                             | No                         | HTTP                              |
| `server/discover`    | Supported                      | Supported                  | Supported                         |
| `tools/list`         | Same                           | Same                       | Same                              |
| `tools/call`         | Same                           | Same                       | Same                              |
| Per-request metadata | Same                           | Same                       | Same                              |

```
IN-MEMORY
+----------------------+
| Python process       |
|                      |
| Client(mcp)          |
|     |                |
|     v                |
| FastMCP server       |
+----------------------+


STDIO
+--------------------+      stdin/stdout      +--------------------+
| Client process     | <--------------------> | Server subprocess  |
| StdioTransport     |                        | FastMCP server      |
+--------------------+                        +--------------------+


STREAMABLE HTTP
+--------------------+    HTTP POST /mcp     +--------------------+
| Client process     | <-------------------> | HTTP server        |
| StreamableHttp     |                       | FastMCP server      |
+--------------------+                       +--------------------+
```

---

This server supports both transports — `stdio/HTTP`.
The tool, resource, and prompt are unchanged.

## **2. Client — `client.py`**

**`In-memory`:** The client imports the **mcp** instance from `server.py`.

**`STDIO`:** The client selects `StdioTransport` and launches `server.py` as a
separate process.

**`HTTP`:** The client selects `StreamableHttpTransport` and connects to the
independently running server.

Selects transport, runs server/discover, tools/list, tools/call, and verifies
the protocol and capabilities.

All three run the same inspection workflow:

- `server/discover`,
- `tools/list`,
- `tools/call`,
- protocol version assertions, and
- client capability inspection.

The resource, prompt, and elicitation handler remain shared.

### 1. Transport Selection - `client.py`

```python

import sys
from pathlib import Path

from server import mcp
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport


def client_source(mode: str) -> Any:
    """Use the same examples with in-memory, stdio, or HTTP transport."""
    if mode == "in-memory":
        return mcp
    if mode == "stdio":
        return StdioTransport(
            command=sys.executable,
            args=[
                str(Path(__file__).resolve().with_name("server.py")),
                "--transport",
                "stdio",
            ],
        )
    if mode == "http":
        return StreamableHttpTransport(url="http://127.0.0.1:8000/mcp")
    raise ValueError(f"Unsupported mode: {mode}")
```

The shared inspection function then uses `Client(client_source(mode), ...)`.

### 2. What happens internally?

```
                    +-------------------+
                    |  CLI mode chosen  |
                    +---------+---------+
                              |
                +-------------+-------------+
                |             |             |
                v             v             v
           IN-MEMORY        STDIO          HTTP
                |             |             |
                v             v             v
           Client(mcp)    Subprocess     HTTP /mcp
                |             |             |
                +-------------+-------------+
                              |
                              v
                       server/discover
                              |
                              v
                        tools/call
                              |
                              v
                   inspect_request_metadata
                              |
                              v
                   Inspect request metadata
                              |
                              v
                    Assert protocol version
                    Assert elicitation support
                              |
                              v
                         tools/list
                              |
                              v
                        Print results
```

### 3. What actually happens in your `client.py`

Your code contains:

```python
async with Client(
        transport=client_source(transport_name),
        name="lesson-1-client",
        elicitation_handler=decline_elicitation,
) as client:
```

**At this point, FastMCP automatically performs discovery.**

**Next:** if `--example discovery` or `--example both` is selected

code executes:

```python
discovery = client.session.discover_result
```

This reads the result of discovery that already happened.

**Explicit discovery call**

```python
async with Client(mcp) as client:
    discovery = await client.session.discover()

    print(discovery.supported_versions)
    print(discovery.capabilities)
```

**Important:**
By the time execution enters `async with`, FastMCP has already performed 
discovery automatically. Calling `client.session.discover()` again 
returns the stored result rather than sending another request.

Later, code executes:

```python
await client.list_tools()
```

This answers the question - `What specific tools are available?`.

**Next:** if `--example metadata` or `--example both` is selected

Invoke `inspect_request_metadata` with `call_tool()` to demonstrate how client
capabilities arrive on an ordinary request.

```python
observed = (await client.call_tool("inspect_request_metadata")).data
```

### 4. The actual request sequence

The exact execution order in your code is server/discover, then tools/call, then
tools/list.

```
CLIENT                                SERVER
  |                                     |
  |-- server/discover ----------------->|
  |<-- supported versions, capabilities-|
  |                                     |
  |   FastMCP stores discover_result    |
  |                                     |
  |-- tools/call ---------------------->|
  |   inspect_request_metadata          |
  |                                     |
  |                  Reads metadata     |
  |                  from this request  |
  |                                     |
  |<-- protocol version + client caps --|
  |                                     |
  |-- tools/list ---------------------->|
  |<-- registered tool definitions -----|
```

---

## **2. Server —` server.py`**

### 1. Why your `server.py` has an inspection tool

Your server defines:

```python
@mcp.tool
def inspect_request_metadata(ctx: Context) -> dict[str, Any]:
    capabilities = ctx.session.client_capabilities
```

This tool exists to demonstrate per-request client capabilities, not server
discovery.

It answers a different question:

- `server/discover`: What features does the server support?
- `inspect_request_metadata`: What capabilities did the client advertise on this
  request?
- `tools/list`: What specific tools are available?
  The inspection tool reports the client capabilities received with its own
  tools/call request.

---

## **4. Run commands**

Install the specified FastMCP version:

```shell
python -m pip install "fastmcp==4.2.0"
```

| **Mode**        | Server                              | **Client**                               |
|-----------------|-------------------------------------|------------------------------------------|
| In-memory       | Not required                        | `python client.py --transport in-memory` |
| STDIO           | Started automatically               | `python client.py --transport stdio`     |
| Streamable HTTP | `python server.py --transport http` | `python client.py --transport http`      |

For HTTP, run the server and client commands in separate terminals.
Endpoint: http://127.0.0.1:8000/mcp

## **5. Expected verification**

**For either transport, the important output should include:**

```
server/discover response
  supported versions: ['2026-07-28', ...]
  server capabilities: [...]

tools/list response
  Name: inspect_request_metadata
  Description: Return protocol metadata ...

tools/call metadata observed by the server
  io.modelcontextprotocol/protocolVersion: 2026-07-28
  io.modelcontextprotocol/clientCapabilities:
    {
      "elicitation": ...
    }

Verified: the client advertised optional elicitation support.
```

## **6. Notes**

**Important:** In FastMCP 4.x, `server/discover` is a protocol-discovery
operation, not the old `initialize` handshake. The `2026-07-28` protocol carries
version and client capabilities with each request. The client may also negotiate
an older protocol if connecting to an older server.&#x20;

For this example, the strict assertions deliberately fail if the modern protocol
is not negotiated.

For HTTP, a `Connection refused` error normally means the HTTP server has not
started or the client URL/port differs. For stdio, the most common setup failure
is using a different Python environment for the subprocess; `sys.executable`
avoids that mismatch.

The examples are based on the official FastMCP 4.x API and PyPI 4.2.0 release.

