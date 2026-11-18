# Host, client, model, and server

**Outcome:** Locate each participant and assign responsibility for one tool invocation.

**Prerequisites:** [01: Why MCP exists](01-why-mcp.md).

## Separate decisions from execution

### The main participants

```
Host
└── Client
    └── Server
        ├── Tools
        ├── Resources
        └── Prompts
```

#### Host

A MCP host is the **application containing the AI experience**.
It orchestrates MCP clients.

**Examples:** AI desktop application, IDE, agent runtime, or chat application.

#### Client

An MCP client is the **protocol participant inside the host** that communicates
with one MCP server.

Professional wording:

> “The host owns the user interaction, while its MCP client manages protocol
> communication with the server.”

#### Server

An MCP server is a program that **exposes capabilities and context**.

It does **not necessarily contain an LLM**. It may simply expose database
queries, API calls, calculations, files, or business operations.

A technically accurate sentence would be:
> “The host creates an MCP client which negotiates capabilities with the
> server over the stdio transport.”


```
+---------------------- Host ----------------------+
| User interface --> orchestration <--> model      |
|                         |                        |
|                     MCP client                   |
+-------------------------|------------------------+
                          |
                      transport
                          |
                     MCP server
                          |
                   ticket service
                          |
                     ticket store
```

A client is a role, not necessarily a separate operating-system process.
A server can run in another process or machine; an in-memory test can place
client and server objects in the same process.

## Trace the responsibilities

Suppose the user asks “Is T-100 open?” The host chooses which capabilities to
show the model and how to apply its approval policy. The model proposes
`get_ticket` with `ticket_id="T-100"`. The client encodes and sends that
invocation. The server validates the request and dispatches to the handler.
The business service reads the record. The client receives the result, and the
host decides how to present or use it.

Discovery does not automatically place a tool into a model prompt. The host
must translate or expose the discovered contract in the form its model API
expects. This is why a successful scripted client proves protocol connectivity
without proving a particular AI host will use the tool correctly.

## Ownership determines failures

If a model chooses the wrong ticket ID, inspect host context and tool
descriptions. If the subprocess cannot start, inspect client launch settings.
If the tool is unknown, inspect registration and the discovered catalog.
If the wrong user's ticket is returned, inspect server authorization and
data access.

These are different layers. Changing the system prompt cannot repair a
missing server executable. Changing transport cannot repair an authorization
rule that trusts a caller-supplied tenant ID.

## Several servers

A host may manage several client/server relationships. A ticket server and a
document server can be separate integrations with different identities and
permissions. A single server can also expose many tools. Neither “one tool
equals one server” nor “one host equals one server” is a protocol rule.

Treat each boundary as a place where data and authority cross. A result from a
document service is information, not an instruction to disable ticket-service
access checks.

**Worked observation:**

> In the supplied lab, `client.py` is a scripted caller. It has no model and
> no chat interface. This deliberately isolates discovery and execution from
> model selection and reasoning.

**Professional articulation:**

> “The host owns orchestration, the client owns protocol communication, and
> the server exposes a controlled boundary around application capabilities.”

## Sources and next step

- [Archive: conversations/chatgpt/1_FirstMCPTool_InProcess.md](../../conversations/chatgpt/1_FirstMCPTool_InProcess.md)
- [Archive: definitions.md](../../definitions.md)
- [Official reference](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture) — checked 2026-11-15.

Next: [JSON-RPC requests, responses, and notifications](03-json-rpc.md).

