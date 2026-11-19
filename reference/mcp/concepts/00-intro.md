# Start here: the MCP mental model

This page is for a learner who has never used the Model Context Protocol (MCP).
It gives you the few ideas and words needed before concept 01.

**Outcome:** Explain, in plain language, what MCP connects and recognize its
four main participants: host, model, client, and server.

**Prerequisites:** Basic Python function calls are helpful, but not required.
You do not need an AI account, database, Docker, or web-server experience.

## Begin with an ordinary Python function

Imagine that a support application needs to look up a ticket. Without MCP, the
application can call a normal Python function:

```python
TICKETS = {
    "T-100": {"id": "T-100", "status": "open"},
}


def get_ticket(ticket_id: str) -> dict:
    return TICKETS[ticket_id]


print(get_ticket("T-100"))
```

Expected output:

```text
{'id': 'T-100', 'status': 'open'}
```

This is enough when the function and its only caller live in the same program.
MCP becomes useful when an AI application needs to use capabilities supplied by
another program through a standard interface.

## The smallest useful MCP picture

```text
User
  |
  v
Host application <--> Model
  |
  | owns an MCP client
  v
MCP client ===== messages ===== MCP server
                                  |
                                  v
                           ticket function
```

The double line is the MCP communication boundary. It can be local, between two
processes on one computer, or remote, across a network.

**Host:**

> The application the user interacts with. It manages the model, user
> experience, permissions, and one or more MCP clients.

**Model:**

> The language model that can suggest using a capability. The model does not
> directly open the server's database or execute the server's Python function.

**MCP client:**

> The part of the host that speaks MCP to one server. It sends requests and
> receives results.

**MCP server:**

> A program that publishes controlled capabilities, such as looking up a
> ticket. It validates requests and calls the application or business code that
> performs the work.

The word *server* describes a role. During an in-memory test, the client and
server can be objects inside one Python process. In deployment, the server can
run as a separate process or on another machine.

## What MCP standardizes

MCP is a **protocol**. A protocol is a shared set of communication rules. It
defines message shapes, operation names, and interaction behavior so programs
built independently can understand each other.

MCP standardizes three common server building blocks:

**Tool:**

> An operation that can be called. Example: `get_ticket("T-100")`.

**Resource:**

> Readable content identified by a URI (Uniform Resource Identifier). Example:
> `ticket://T-100`.

**Prompt:**

> A reusable message template. Retrieving a prompt does not run a language
> model by itself.

```text
MCP server
  |-- tool:     perform an operation
  |-- resource: read identified content
  `-- prompt:   retrieve a message template
```

These are called **primitives**, meaning the basic kinds of component supplied
by the protocol. You will study each one separately. You do not need to
memorize their wire messages now.

## Messages and transport are different ideas

Two layers work together:

```text
MCP meaning:       "Call the get_ticket tool"
                         |
                         v
JSON-RPC message:  structured request with an ID
                         |
                         v
Transport:         carries the message by stdio or HTTP
```

**JSON-RPC:**

> The message envelope MCP uses for requests, responses, and notifications.
> JSON-RPC supplies fields such as `method` and `id`; MCP defines what methods
> such as `tools/call` mean.

**Transport:**

> The mechanism that carries messages. This course uses `stdio` for a local
> child process and Streamable HTTP for a network service.

Changing the transport does not change what `get_ticket` does. It changes how
the request reaches the server.

## A first FastMCP preview

FastMCP is a Python framework that implements MCP details. The decorator below
registers a normal function as an MCP tool:

```python
from fastmcp import FastMCP

mcp = FastMCP("Ticket learning service")


@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read one support ticket. Does not change it."""
    return {"id": ticket_id, "status": "open"}
```

This snippet shows the shape of the code; concept 07 provides the complete,
tested setup and run commands. Learn the protocol roles before depending on the
framework to hide them.

## Version note for this course

MCP has dated protocol revisions. This course targets the modern
`2026-07-28` revision and labels older, stateful behavior separately. A protocol
revision is not the same thing as a FastMCP package version or a Python version.
Read [the version baseline](../VERSIONS.md) when comparing examples from
different dates.

You do not need version negotiation details yet. Concept 04 introduces them
after JSON-RPC requests are clear.

## Beginner learning path

For a first pass, follow these stages:

1. Understand the problem and roles in concepts 01 and 02.
2. Learn the message shape in concepts 03 and 04.
3. Learn tool contracts and framework registration in concepts 05 and 06.
4. Run the small lab in concept 07.
5. Add process, network, security, and production boundaries only after the
   in-memory example makes sense.

The course keeps one synthetic ticket example so each chapter changes only one
important idea at a time.

**Say it professionally:**

> “MCP is a standard communication boundary between an AI host and a server
> that exposes controlled tools, resources, and prompts. The host orchestrates
> model use; the server still owns validation and business behavior.”

Next: [Why MCP exists](01-why-mcp.md).
