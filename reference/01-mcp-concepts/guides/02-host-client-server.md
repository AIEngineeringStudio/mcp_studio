# Host, model, client, and server

**Outcome:** Identify the four participants in one MCP tool call and explain
which participant owns each responsibility.

**Prerequisites:** [01: Why MCP exists](01-why-mcp.md).

## First separate the four roles

The words *host*, *model*, *client*, and *server* name different roles. They can
live in the same application or in separate processes, but their
responsibilities remain different.

```
+------------------------ Host application -------------------------+
|                                                                   |
|  User interface <--> orchestration <--> language model            |
|                              |                                    |
|                         MCP client                                |
+------------------------------|------------------------------------+
                               | MCP messages
                               v
                          MCP server
                               |
                               v
                         ticket service
```

**Host:**

> The application the user interacts with. It owns the AI experience,
> coordinates the model, creates MCP clients, and applies user-facing policy.

Examples include a chat application, an IDE, or an agent runtime.

**Model:**

> The language model used by the host. It can propose a tool name and arguments
> after seeing a tool description. A proposal is data; it does not directly
> execute the server's function.

**MCP client:**

> The protocol component inside the host that communicates with one MCP server.
> It encodes requests, sends them, and decodes results.

**MCP server:**

> The protocol component that publishes tools, resources, and prompts. It
> validates and dispatches calls to application code.

**Dispatch:**

> Selecting the registered handler that matches an incoming operation, then
> calling it.

An MCP server does not need to contain a language model. It may expose database
queries, calculations, files, or calls to an existing business API.

## “Client” and “server” are roles, not always machines

A beginner often hears *server* and imagines a remote computer. In MCP, the word
first describes which side provides capabilities.

```
In-memory test:  [client object | server object] in one Python process

Local stdio:     [host + client] <--> [server child process]

Remote HTTP:     [host + client] <---- network ----> [server process]
```

The same tool contract can be tested in all three arrangements. The later
transport guides add one boundary at a time.

## Trace one successful lookup

Suppose the user asks, “Is T-100 open?”

1. The **host** receives the user's message.
2. The host gives the **model** a description of `get_ticket`.
3. The model proposes `get_ticket` with `ticket_id="T-100"`.
4. The host decides whether the proposal is allowed.
5. The **MCP client** sends a structured request.
6. The **MCP server** validates it and dispatches to the handler.
7. The ticket service reads the record and returns data.
8. The client receives the result; the host decides how to present it.

```
Host decision -> client communication -> server execution -> host presentation
```

This separation matters because a failure at one role needs a fix at that role.

## See the roles in Python

The course lab uses a scripted client so protocol behavior can be learned
without a model:

```python
from fastmcp import Client, FastMCP

server = FastMCP("Ticket service")


@server.tool
def get_ticket(ticket_id: str) -> dict:
    return {"id": ticket_id, "status": "open"}


async def inspect_server() -> None:
    async with Client(server) as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools])
```

Here, `server` and `client` are in the same process. There is no model and no
chat interface. This is intentional: it proves discovery and communication
before adding model behavior.

The complete runnable version appears in [concept 07](07-in-memory-client.md).

## Ownership helps diagnose failures

**Wrong tool or arguments proposed:**

> Inspect the host's context, tool descriptions, and model interaction.

**Server process does not start:**

> Inspect the client launch command, interpreter, path, and server startup.

**Tool is missing from discovery:**

> Inspect server registration and the actual server instance being served.

**Wrong user's ticket is returned:**

> Inspect server-side identity, authorization, and data access. A system prompt
> is not an authorization control.

**Result is correct but displayed poorly:**

> Inspect host-side result handling and presentation.

## One host can use several servers

A host may create one client for a ticket server and another for a document
server. Each connection can use different identities and permissions.

```
                       client A <--> ticket server
Host application -----+
                       client B <--> document server
```

A single server can expose several tools. MCP does not require one server per
tool or one server per host.

Treat every boundary as a place where data and authority cross. Text returned
by a document server is information; it is not permission to bypass the ticket
server's access checks.

**Say it professionally:**

> “The host owns orchestration and user policy, the model proposes actions, the
> MCP client owns protocol communication, and the server exposes and enforces a
> controlled capability boundary.”

## Sources and next step

- [Archived in-process tool example](../fastMcp-fastApi-uvicorn-ngnix-docker/1_FirstMCPTool_InProcess.md)
- [Archived definitions](../../../_archive/temp/definitions.md)
- [Official MCP architecture guide](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)

Next: [JSON-RPC requests, responses, and notifications](03-json-rpc.md).
