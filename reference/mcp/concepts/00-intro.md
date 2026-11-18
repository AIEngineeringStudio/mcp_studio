## Baseline

- MCP protocol:
    - 2025-11-25: stateful architecture
    - 2026-07-28: stateless-first architecture
- Transport:
    - stdio
    - Streamable HTTP
- FastMCP:
    - 3.4.5, the current stable release
    - > = 4
- Python
    - Modern Python with type hints.

We will learn the stable stateful protocol first, then explicitly study the new
stateless architecture as a migration.

## Course structure

1. Architecture, JSON-RPC, lifecycle, capabilities, stdio
2. **Tools** — discovery, schemas, execution, errors, structured results
3. **Resources** — URIs, reads, templates, subscriptions
4. **Prompts** — discovery, arguments, generated messages
5. **Client capabilities** — roots, elicitation, sampling  (deprecated in  
   `MCP 2026-07-28`)
6. **Protocol utilities** — progress, cancellation, logging, pagination and
   completion,
7. **Streamable HTTP**
8. **Authentication and authorization**
9. **Context, lifecycle state and concurrency**
10. **FastMCP-specific composition** — providers, proxies, transforms, generated
    servers
11. **Testing, observability, security and production deployment**
12. **MCP 2026-07-28 stateless architecture + FastMCP 4 migration**

The protocol separates server primitives into tools, resources and prompts,
while client-side capabilities include sampling, roots and elicitation.

Utilities such as logging, completion, progress and cancellation sit across
these features.

> Sampling is deprecated in `MCP 2026-07-28`.
> It still exists for compatibility, but the specification says new
> implementations should not add it.
> Suggested replacement is a direct LLM-provider integration.
>
> We should still learn it because it exposes several important MCP concepts:
> client capabilities, model abstraction, multi-round interactions, tool loops,
> trust boundaries, and the difference between the 2025-11-25 and 2026-07-28
> protocol architectures.


## Concept Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP CONCEPT HIERARCHY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROTOCOL LAYER                                                             │
│  ├── JSON-RPC 2.0 ─────────── message format                                │
│  └── Transport ────────────── How messages travel                           │
│       ├── Streamable HTTP                                                   │
│       └── stdio                                                             │
│                                                                             │
│  COMPONENT LAYER                                                            │
│  ├── MCP Server ───────────── exposes capabilities                          │
│  └── MCP Client ───────────── manages protocol communication                │
│                                                                             │
│  CAPABILITY LAYER                                                           │
│  ├── Tools ────────────────── executable operation                          │
│  ├── Resources ────────────── readable context identified by a URI          │
│  ├── Prompts ──────────────── reusable interaction templates                │
│  ├── Sampling ─────────────── server can request an LLM completion          │
│  └── Elicitation ──────────── server can ask the user for input             │
│                                                                             │
│  LIFECYCLE LAYER                                                            │
│  ├── Initialization ───────── Capability negotiation                        │
│  ├── Discovery ────────────── List available items                          │
│  ├── Invocation ───────────── Call tools / read resources                   │
│  └── Shutdown ─────────────── Clean disconnect                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## High-Level Architecture

```


                     ┌──────────────────────────┐
                     │        MCP CLIENT        │
                     │   ( Agent / App / IDE )  │
                     └────────────┬─────────────┘
                                  │ JSON-RPC Messages
                                  ▼
                     ┌──────────────────────────┐
                     │        TRANSPORT         │
                     ├──────────────────────────┤
                     │     stdio                │
                     │     Streamable HTTP      │
                     └────────────┬─────────────┘
                                  │ JSON-RPC Messages
                                  ▼
                     ┌──────────────────────────┐
                     │        MCP SERVER        │
                     │ (tools + data + prompts) │
                     └────────────┬─────────────┘
                                  │                             
          ┌───────────────────────┼─────────────────────────┐
          │                       │                         │
          ▼                       ▼                         ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ 
│         TOOLS        │ │      RESOURCES       │ │       PROMPTS        │ 
│       (actions)      │ │        (data)        │ │     (templates)      │ 
├──────────────────────┤ ├──────────────────────┤ ├──────────────────────┤ 
│   tools/list         │ │  resources/list      │ │   prompts/list       │ 
│   tools/call         │ │  resources/read      │ │   prompts/get        │ 
│   streaming          │ │  subscriptions       │ │   arguments          │
│   progress           │ │  templates           │ │   sampling           │ 
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘   
```

## Term Definitions

```
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ TERM             │ DEFINITION                                              │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Host         │ Application with AI experience.                         │
│                  │ MEMORIZE: "Host = Orchestrates clients"                 │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Server       │ EXPOSES tools/resources/prompts.                        │
│                  │ MEMORIZE: "Server = Provider = Exposes"                 │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Client       │ CALLS what a server exposes.                            │
│                  │ MEMORIZE: "Client = Consumer = Calls"                   │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Tool             │ Invocable function.                                     │
│                  │ Has: name, description, input schema, output.           │
│                  │ Example: search_transactions, send_email                │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Resource         │ Read-only data by URI.                                  │
│                  │ Has: URI, name, mime type, contents.                    │
│                  │ Example: file://config.json, db://users                 │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Prompt           │ Reusable template with arguments                        │
│                  │ Has: name, description, arguments, messages.            │
│                  │ Example: "summarize_document" prompt template           │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Capability       │ Declared support for an optional protocol feature       │
│                  │ Negotiated during initialization.                       │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Transport        │ Mechanism carrying protocol messages                    │
│                  │ Options: Streamable HTTP, stdio                         │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Protocol message │ JSON-RPC request, response or notification              │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Wire format      │ Actual bytes/messages transmitted between endpoints     │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ JSON-RPC 2.0     │ The message format used by MCP.                         │
│                  │ Every message has: jsonrpc, method/result, id           │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Session          │ A stateful connection between client and server.        │
└──────────────────┴─────────────────────────────────────────────────────────┘
```