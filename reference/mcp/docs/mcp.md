# MCP From First Principles

```
┌───────────────────────────────┐
│ AI application / MCP host     │
│                               │
│   MCP client                  │
└───────────────┬───────────────┘
                │ Streamable HTTP
                ▼
┌───────────────────────────────┐
│ Nginx                         │
│ - TLS termination             │
│ - Reverse proxy               │
│ - Forwarded headers           │
└───────────────┬───────────────┘
                │ HTTP
                ▼
┌──────────────────────────────────┐
│ Uvicorn                          │
│ - ASGI server / process runtime  │
└───────────────┬──────────────────┘
                │ ASGI
                ▼
┌─────────────────────────────────┐
│ FastAPI                         │
│ - Lifespan, health, middleware  │
│                                 │
│   Mounted FastMCP app           │
└───────────────┬─────────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Application services          │
│ Databases, APIs, files        │
└───────────────────────────────┘

Everything packaged with Docker.
Dependencies managed with uv.
```

## Learning Roadmap

| Increment | What we build                   | Concepts                                             |
|-----------|---------------------------------|------------------------------------------------------|
| 1         | In-memory MCP server and client | Tools, schemas, discovery, invocation                |
| 2         | Local stdio server              | Processes, stdin/stdout, transport boundary          |
| 3         | Resources and prompts           | MCP primitives and URI design                        |
| 4         | Real service layer              | Async I/O, validation, errors, dependency boundaries |
| 5         | Streamable HTTP server          | HTTP transport and ASGI                              |
| 6         | FastAPI integration             | Lifespan, application state, health checks           |
| 7         | Uvicorn runtime                 | Workers, graceful shutdown, concurrency              |
| 8         | Nginx reverse proxy             | Upstreams, headers, buffering, TLS                   |
| 9         | Docker and Compose              | Images, containers, networks, health checks          |
| 10        | Production hardening            | Authentication, observability, timeouts, testing     |

## Part 1: What MCP Actually Is

MCP is a standard contract between an AI application and external capabilities.
It separates two layers:

```
┌────────────────────────────────────────────┐
│ Data layer                                 │
│                                            │
│ JSON-RPC messages                          │
│ Tools, resources, prompts, notifications   │
├────────────────────────────────────────────┤
│ Transport layer                            │
│                                            │
│ stdio or Streamable HTTP                   │
└────────────────────────────────────────────┘
```

MCP currently defines

- stdio for local process communication and
- Streamable HTTP for network communication.

The same logical tool can be used through either transport.
The transport changes how messages travel, not what the tool does.

### The main participants

```
Host
└── Client
    └── Server
        ├── Tools
        ├── Resources
        └── Prompts
```

**Host**

- The user-facing AI application that owns the user interaction.
- Examples include:
    - AI desktop application,
    - IDE,
    - agent runtime,
    - chat application.

**Client**

- The protocol component inside the host that communicates with a particular MCP
  server.

> **Professional wording:**  
> “The host owns the user interaction, while its MCP client manages protocol
> communication with the server.”

**Server**

- The program exposing capabilities and context.
- It does not necessarily contain an LLM.
- It may simply expose database queries, API calls, calculations, files, or
  business operations.

### MCP Primitives

**Tool**

- An executable operation.
- Use a tool when something must be performed. Typical verbs:
    - Search
    - Calculate
    - Create
    - Update
    - Send
    - Delete

```python
def create_invoice(customer_id: str, amount: float) -> dict:
    ...
```

**Resource**

- Readable context identified by a URI.
- Use a resource when something must be retrieved or inspected.

```
config://application
customer://123/profile
schema://orders
```

**Prompt**

- A reusable interaction template.
- Use a prompt when the server needs to communicate with the host to provide
    - a recommended workflow or
    - structured instruction.

## FastMCP

FastMCP implements the MCP protocol. 

FastMCP turns ordinary Python functions into MCP tools and derives the tool
description and input schema from the function’s docstring and type
annotations.

It handles 
- session initialization, 
- tool discovery, 
- tool calls, 
- notifications, 
- elicitation, and 
- result serialization.

