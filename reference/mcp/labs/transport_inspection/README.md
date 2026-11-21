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

## **2. Server —` server.py`**

This server supports both transports — `stdio/HTTP`.
The tool, resource, and prompt are unchanged.

## **3. Client — `client.py`**

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

### The important part of `client.py`

```python

import sys
from pathlib import Path

from server import mcp
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport


def client_source(mode: str):
    if mode == "in-memory":
        return mcp

    if mode == "stdio":
        return StdioTransport(
            command=sys.executable,
            args=[
                str(Path(__file__).resolve().with_name("server.py")),
                "stdio",
            ],
        )

    if mode == "http":
        return StreamableHttpTransport(
            url="http://127.0.0.1:8000/mcp",
        )
    raise ValueError(f"Unsupported mode: {mode}")

```

The shared inspection function then uses `Client(client_source(mode), ...)`.

### **What happens internally?**

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

