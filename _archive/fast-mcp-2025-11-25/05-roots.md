# Lesson 5 — Client Capabilities: Roots

We now cross an important architectural boundary.

Until now, almost everything looked like:

```
CLIENT  ───── request ─────>  SERVER
CLIENT  <──── response ─────  SERVER
```

With **Roots**, stable MCP can do this while processing a client request:

```
CLIENT  ─── tools/call ─────> SERVER
CLIENT  <── roots/list ────── SERVER
CLIENT  ─── roots result ───> SERVER
CLIENT  <── tool result ───── SERVER
```

That is the beginning of **bidirectional MCP**.

For MCP `2025-11-25`, roots are a client capability: clients advertise filesystem roots, and servers can request them through `roots/list`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

---

# 1. First principle: what problem do Roots solve?

Imagine a coding MCP server exposing:

```
search_code()
analyze_repository()
find_dependencies()
```

The server needs to know:

> Which workspace should I operate on?

Bad API:

```python
search_code(
    path="/Users/sid/projects/company/backend/..."
)
```

every single time.

Another bad design:

```
Server guesses:
/
/home
C:\
current working directory
```

MCP introduces **roots** so the client can tell the server:

```
"These are the filesystem areas relevant to this session."
```

Example:

```
file:///home/user/repos/frontend
file:///home/user/repos/backend
```

A root contains a `file://` URI and optionally a human-readable name in MCP `2025-11-25`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

---

# 2. Roots belong to the CLIENT

This is the first major inversion.

Recall:

```
SERVER CAPABILITIES

tools
resources
prompts
```

Now:

```
CLIENT CAPABILITIES

roots
sampling
elicitation
```

The initialization exchange is therefore genuinely symmetric:

```
CLIENT                           SERVER
  │                                │
  │ initialize                     │
  │                                │
  │ client capabilities:           │
  │   roots                        │
  │   sampling                     │
  │   elicitation                  │
  │ ──────────────────────────────>│
  │                                │
  │ server capabilities:           │
  │   tools                        │
  │   resources                    │
  │   prompts                      │
  │<────────────────────────────── │
```

The stable lifecycle explicitly includes `roots`, `sampling`, and `elicitation` as client capabilities. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle?utm_source=chatgpt.com)

Professional phrase:

> **“MCP capability negotiation is asymmetric by feature, but bidirectional at the protocol level.”**

---

# 3. Root capability negotiation

A client supporting roots declares:

```json
{
  "capabilities": {
    "roots": {
      "listChanged": true
    }
  }
}
```

`listChanged` means the client can notify the server when its root set changes. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

Without that capability, the server should not assume it can call:

```
roots/list
```

This is why capability negotiation matters.

Wrong mindset:

```python
await request_roots()
```

without checking anything.

Better mindset:

```
Did client negotiate roots?
        │
        ├── no  → fallback behavior
        │
        └── yes → roots/list
```

---

# 4. Protocol-level `roots/list`

Notice the direction carefully.

The **server** sends:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "roots/list"
}
```

The **client** responds:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "roots": [
      {
        "uri": "file:///home/user/repos/frontend",
        "name": "Frontend"
      },
      {
        "uri": "file:///home/user/repos/backend",
        "name": "Backend"
      }
    ]
  }
}
```

That direction is defined by the stable roots protocol. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

Memorize:

```
tools/list
CLIENT → SERVER

resources/list
CLIENT → SERVER

prompts/list
CLIENT → SERVER


roots/list
SERVER → CLIENT
```

The name alone does not tell you message direction.

---

# 5. Roots are scope, not file contents

Suppose the client responds with:

```
file:///home/user/repos/backend
```

What has actually crossed the wire?

Only:

```
URI
+
optional name
```

Not:

```
repository files
source code
directory listing
file bytes
credentials
```

The stable `roots/list` result contains root descriptors, not file contents. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

So conceptually:

```
ROOT

"Here is an area relevant to your work."

≠

RESOURCE

"Here are contents you can retrieve."
```

A useful distinction:

```
ROOT
filesystem scope/boundary

RESOURCE
MCP-addressable data
```

---

# 6. Roots do not magically grant filesystem access

This is subtle.

Consider a local stdio server:

```
IDE
 │
 │ starts local MCP process
 ▼
MCP server
```

Both may run on the same machine, so:

```
file:///Users/me/project
```

may genuinely be accessible to the server process.

Now consider:

```
Laptop
   │
   │ HTTPS
   ▼
remote MCP server
```

A root such as:

```
file:///Users/me/project
```

does **not** teleport that directory to the remote server.

The protocol only provides the root descriptor; implementations remain responsible for how filesystem access actually works. This follows from the stable protocol's root shape and its requirement that servers validate paths and respect boundaries. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

Professional phrase:

> **“Roots communicate filesystem scope; they are not a file-transfer mechanism.”**

Very important.

---

# 7. Roots are also not authorization

Imagine the client says:

```
allowed root:

file:///projects/acme
```

A badly written server then executes:

```python
open("/etc/passwd")
```

MCP does not physically prevent that call.

The specification requires clients to expose appropriate roots and validate root URIs, while servers should respect root boundaries and validate paths against them. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

So think:

```
ROOTS
   │
   └── declared operating boundary

OS permissions
sandbox
container
ACLs
authorization
   │
   └── actual enforcement mechanisms
```

Professional wording:

> **“Roots define an application-level scope boundary, not a security sandbox.”**

Do not rely on roots as your only security control.

---

# 8. Why this breaks our naive raw MCP implementation

Remember our first server?

Conceptually:

```python
for line in sys.stdin:
    message = json.loads(line)

    if message["method"] == "tools/call":
        ...
        send(response)
```

That model assumes:

```
receive request
execute synchronously
send response
```

Roots introduce:

```
receive tools/call
        │
        ▼
need information from client
        │
        ▼
send roots/list
        │
        ▼
WAIT FOR RESPONSE
        │
        ▼
continue original tools/call
```

Our simple loop is no longer enough.

We need a **request manager**.

---

# 9. First protocol infrastructure upgrade: pending requests

Conceptually:

```python
pending_requests = {}


async def send_request(method, params=None):
    request_id = next_request_id()

    future = create_future()

    pending_requests[request_id] = future

    send({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    })

    return await future
```

Meanwhile the central receive loop must distinguish:

```
incoming JSON-RPC message
          │
          ├── request
          │      └── dispatch handler
          │
          ├── notification
          │      └── dispatch notification
          │
          └── response
                 └── resolve pending Future
```

Pseudo-code:

```python
async def receive_loop():
    async for message in transport:
        if "method" in message and "id" in message:
            # Incoming request
            spawn(handle_request(message))

        elif "method" in message:
            # Incoming notification
            await handle_notification(message)

        elif "id" in message:
            # Response to something we sent
            future = pending_requests.pop(message["id"])
            future.set_result(message)
```

That is a much more realistic protocol implementation.

---

# 10. New jargon: multiplexing

The connection now carries multiple logical conversations:

```
connection
│
├── request #1 tools/call
│      │
│      └── nested request #51 roots/list
│
├── notification
│
└── maybe another request #2
```

This is **multiplexing**.

Related terminology:

- **request correlation**
- **pending request**
- **in-flight request**
- **nested request**
- **bidirectional RPC**
- **request dispatcher**

Professional explanation:

> “Once server-initiated requests are supported, the transport loop must multiplex inbound requests, outbound requests, notifications, and correlated responses.”

That is exactly the sort of implementation detail hidden by an MCP SDK.

---

# 11. Full raw message flow

Suppose our server exposes:

```
analyze_workspace()
```

### Client starts the operation

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/call",
  "params": {
    "name": "analyze_workspace",
    "arguments": {}
  }
}
```

Server realizes:

```
I need the user's workspace.
```

Server sends:

```json
{
  "jsonrpc": "2.0",
  "id": 1001,
  "method": "roots/list"
}
```

Client answers:

```json
{
  "jsonrpc": "2.0",
  "id": 1001,
  "result": {
    "roots": [
      {
        "uri": "file:///workspace/acme",
        "name": "Acme"
      }
    ]
  }
}
```

Server continues the suspended tool call.

Finally:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Analyzed workspace Acme"
      }
    ],
    "isError": false
  }
}
```

So:

```
CALL STACK

tools/call #10
    │
    ├── roots/list #1001
    │       │
    │       └── roots response
    │
    └── tool response #10
```

This pattern is the foundation for Sampling and Elicitation too.

---

# 12. FastMCP client abstraction

At the client side, FastMCP lets you register roots declaratively:

```python
from fastmcp import Client

client = Client(
    "workspace_server.py",
    roots=[
        "file:///home/user/repos/frontend",
        "file:///home/user/repos/backend",
    ],
)
```

When a compatible server asks for roots, the FastMCP client answers from that registration rather than requiring you to manually implement a `roots/list` JSON-RPC handler. [FastMCP](https://gofastmcp.com/clients/roots)

Protocol:

```
server
   │
   └── roots/list
```

FastMCP abstraction:

```
Client(..., roots=[...])
```

---

# 13. Peel the client abstraction

This:

```python
client = Client(
    server,
    roots=[
        "file:///workspace/frontend",
        "file:///workspace/backend",
    ],
)
```

roughly represents:

```
FastMCP Client
│
├── advertise client capability
│      roots
│
├── register roots provider
│
└── when roots/list arrives
       │
       ▼
   construct ListRootsResult
       │
       ▼
   send JSON-RPC response
```

The developer-facing code is configuration.

The underlying protocol behavior is still:

```
server request
→ client request dispatch
→ roots provider
→ protocol response
```

---

# 14. Dynamic roots

Static roots work when you know the workspace at startup.

But imagine an IDE:

```
10:00
user opens Project A

10:20
user switches to Project B
```

The root set is runtime state.

FastMCP supports a callback:

```python
from fastmcp import Client
from fastmcp.client.roots import RequestContext


async def roots_callback(
    context: RequestContext,
) -> list[str]:
    return [
        "file:///workspace/current-project"
    ]


client = Client(
    "workspace_server.py",
    roots=roots_callback,
)
```

FastMCP invokes the callback when the server asks for roots; its current client documentation supports both static lists and dynamic callbacks. [FastMCP](https://gofastmcp.com/clients/roots)

Now:

```
roots/list
    │
    ▼
roots_callback(...)
    │
    ▼
current application state
    │
    ▼
ListRootsResult
```

This is a **provider callback** pattern.

---

# 15. Why dynamic providers matter

Suppose you instead captured the workspace once:

```python
roots = [current_workspace]
```

Then the user changes workspace.

Your MCP state becomes stale.

Dynamic resolution means:

```
request time
    │
    ▼
resolve current roots
```

rather than:

```
startup time
    │
    ▼
freeze roots forever
```

Professional terminology:

> **eager configuration** versus **lazy/dynamic resolution**

---

# 16. Server-side FastMCP 3 abstraction

For the FastMCP 3.x / MCP `2025-11-25` baseline we have been learning, server code could request roots through the injected `Context`:

```python
from fastmcp import Context, FastMCP

mcp = FastMCP("WorkspaceServer")


@mcp.tool
async def inspect_workspace(
    ctx: Context,
) -> list[str]:
    roots = await ctx.list_roots()

    return [
        str(root.uri)
        for root in roots
    ]
```

Conceptually:

```
ctx.list_roots()
       │
       ▼
FastMCP / MCP SDK
       │
       ▼
JSON-RPC roots/list
       │
       ▼
client
       │
       ▼
ListRootsResult
       │
       ▼
Python Root objects
```

FastMCP 4 removes `ctx.list_roots()` because the newer `2026-07-28` protocol removes the session back-channel used by this request pattern; we will cover that migration separately rather than mixing protocol eras here. [FastMCP](https://gofastmcp.com/more/faq?utm_source=chatgpt.com)

---

# 17. Notice what FastMCP is really abstracting

`ctx.list_roots()` looks like an ordinary Python method:

```python
roots = await ctx.list_roots()
```

But it is not a local getter.

Under stable MCP it can perform a **network/protocol round trip**:

```
Python method call
      │
      ▼
serialize roots/list
      │
      ▼
transport
      │
      ▼
remote client handler
      │
      ▼
response
      │
      ▼
deserialize
      │
      ▼
resume coroutine
```

This means:

```python
await ctx.list_roots()
```

has very different performance and failure semantics from:

```python
self.roots
```

Professional phrase:

> **“`ctx.list_roots()` is an RPC abstraction, not an in-process property lookup.”**

That distinction matters during performance reviews.

---

# 18. Never hide network assumptions

Bad:

```python
for item in items:
    roots = await ctx.list_roots()
```

If there are 1,000 items, you may create unnecessary protocol round trips.

Better:

```python
roots = await ctx.list_roots()

for item in items:
    ...
```

General distributed-systems rule:

```
Python-looking API
does not imply
local-call cost
```

The same warning will become even more important with Sampling.

---

# 19. Root list changes

Suppose:

```
before

file:///workspace/frontend
```

User adds another project:

```
after

file:///workspace/frontend
file:///workspace/backend
```

If the client advertised:

```json
{
  "roots": {
    "listChanged": true
  }
}
```

it must notify the server:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/roots/list_changed"
}
```

The server can then request the new root list via `roots/list`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

Notice:

```
notification
does not contain roots
```

Instead:

```
roots changed
      │
      ▼
notification
      │
      ▼
server calls roots/list
```

Same **invalidation pattern** we saw with Resources.

---

# 20. Why send invalidation instead of the new roots?

Suppose multiple changes happen rapidly.

A notification says:

```
"Your cached state is stale."
```

rather than embedding authoritative state directly.

That creates:

```
notification
    │
    ▼
re-fetch canonical state
```

This is common distributed-systems design:

- cache invalidation
- event notification
- canonical re-read

Professional phrase:

> **“`notifications/roots/list_changed` is an invalidation signal; `roots/list` remains the authoritative read operation.”**

---

# 21. Root identity

A stable root is:

```json
{
  "uri": "file:///home/user/repos/backend",
  "name": "Backend Repository"
}
```

The identity is:

```
uri
```

The name is display metadata. MCP `2025-11-25` requires root URIs to use `file://`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

So avoid using:

```
name = "Backend"
```

as your routing identity.

Names can change.

URIs represent the root.

---

# 22. Path validation

Suppose the root is:

```
file:///workspace/acme
```

and the model requests:

```
../../etc/passwd
```

A secure server should resolve the requested path and verify it stays within the allowed root. The stable specification explicitly tells servers to validate paths against roots and clients to validate root URIs. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

Conceptually:

```
ROOT

/workspace/acme

requested
/workspace/acme/src/app.py
        │
        └── valid


requested
/workspace/acme/../../etc/passwd
        │
        ▼
normalized
/etc/passwd
        │
        └── OUTSIDE ROOT
```

This is a **path traversal** problem.

---

# 23. Don't do naive string prefix checks

This is unsafe:

```python
if path.startswith(root):
    allow()
```

Example:

```
root:
/workspace/app

path:
/workspace/application-secrets
```

String prefix:

```
YES
```

Filesystem containment:

```
NO
```

You want canonical path resolution plus actual parent/child containment checks.

Roots tell you the boundary; your filesystem code must enforce it.

---

# 24. Multiple roots

Clients can expose multiple roots:

```
Frontend
file:///repos/frontend

Backend
file:///repos/backend

Shared
file:///repos/shared
```

This lets the server reason about a workspace consisting of several repositories. The stable specification explicitly includes a multiple-repository example. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)

Architecturally:

```
WORKSPACE

├── frontend root
├── backend root
└── shared root
```

not:

```
one MCP session
=
exactly one folder
```

---

# 25. Root-aware Tool design

Suppose we expose:

```python
@mcp.tool
async def search_code(
    query: str,
    ctx: Context,
):
    roots = await ctx.list_roots()
```

The public tool schema contains:

```
query
```

but not:

```
ctx
roots
```

The workspace scope comes from the MCP client capability.

So the actual execution context is:

```
explicit arguments
      +
negotiated client context
```

This distinction is useful:

```
TOOL ARGUMENT

supplied explicitly for invocation


ROOT

environment/context supplied
by MCP client capability
```

---

# 26. Hidden dependency tradeoff

Roots are convenient, but there is a design cost.

Compare:

```python
analyze_repo(
    path="/workspace/acme"
)
```

versus:

```python
analyze_repo(
    ctx: Context
)
# internally asks for roots
```

The first has an explicit dependency:

```
path visible in schema
```

The second has a contextual dependency:

```
requires roots capability
```

Neither is universally better.

Use roots when:

```
workspace context belongs to the client/session
and many operations share it
```

Prefer an explicit argument when:

```
the caller should deliberately choose a particular path
per operation
```

Professional phrase:

> **“Roots trade explicit per-call parameters for negotiated ambient workspace context.”**

That is a real API-design choice.

---

# 27. Capability fallback design

A robust tool should consider:

```
What if client does not support roots?
```

Possible designs:

### A. Require Roots

```
No roots capability
→ fail clearly
```

Appropriate when the server is fundamentally workspace-based.

### B. Explicit fallback

Tool takes:

```python
path: str | None
```

Logic:

```
path provided?
   │
   ├── yes → use it
   │
   └── no
        │
        └── roots supported?
               │
               ├── yes → resolve root
               └── no → error
```

### C. Server-owned workspace

The server already knows the workspace independently.

Then roots may be unnecessary.

The important thing is deciding deliberately rather than assuming every MCP client implements every client capability.

---

# 28. Complete Protocol → FastMCP map

| MCP protocol | FastMCP 3 abstraction |
|---|---|
| client `roots` capability | `Client(..., roots=...)` |
| root provider | static list or callback |
| `roots/list` request | `ctx.list_roots()` |
| `ListRootsResult` | Python root objects |
| `Root.uri` | root URI |
| `Root.name` | optional display name |
| root change notification | handled through client protocol support |
| request/response correlation | framework |
| nested RPC | framework |
| capability detection | framework/context |

FastMCP's current client still exposes `roots=` with both static and dynamic providers for interoperability, while its v4 server API removed the old push-style `ctx.list_roots()` abstraction. [FastMCP](https://gofastmcp.com/clients/roots)

---

# 29. The deeper architecture lesson

Roots are useful, but the bigger lesson is this:

Before Roots, you could imagine MCP as:

```
client
   │
   ▼
server
```

After Roots:

```
              requests
CLIENT ───────────────────> SERVER

CLIENT <─────────────────── SERVER
              requests
```

So each peer needs machinery for:

```
sending requests
receiving requests
sending responses
receiving responses
handling notifications
correlating IDs
tracking capabilities
```

That is substantially closer to a **peer-to-peer RPC session** than to a conventional REST API.

The roles remain client/server, but message direction is not simply request-direction = client-to-server in the stable protocol.

---

# 30. Jargon checkpoint

| Term | Meaning |
|---|---|
| **Root** | Client-exposed filesystem scope |
| **Client capability** | Feature implemented by the MCP client |
| **Server-initiated request** | Request originating from server toward client |
| **Bidirectional RPC** | Either participant can initiate protocol requests |
| **Nested request** | RPC issued while processing another RPC |
| **In-flight request** | Request sent but not yet resolved |
| **Request correlation** | Matching a response to its originating request ID |
| **Multiplexing** | Multiple logical message flows sharing one connection |
| **Ambient context** | Information available outside explicit function arguments |
| **Scope boundary** | Declared area in which work should occur |
| **Path traversal** | Escaping a permitted directory using path manipulation |
| **Invalidation notification** | Signal that previously cached state should be refreshed |
| **Dynamic provider** | Callback resolving values at request time |
| **Back-channel** | Existing session path allowing server-to-client requests |

A professional explanation:

> **“Roots are a client capability that lets a stable MCP server discover filesystem scope through a server-initiated `roots/list` request. FastMCP abstracts the client side through `Client(..., roots=...)` and, in FastMCP 3, the server side through `ctx.list_roots()`. Because that method represents a nested RPC rather than a local lookup, implementations need request multiplexing and capability-aware fallback behavior.”**

---

# 31. Hands-on exercise

Build:

```python
@mcp.tool
async def workspace_info(
    ctx: Context,
) -> dict:
    ...
```

Have it return:

```json
{
  "root_count": 2,
  "roots": [
    "file:///workspace/frontend",
    "file:///workspace/backend"
  ]
}
```

Create the FastMCP client with:

```python
Client(
    "server.py",
    roots=[
        "file:///workspace/frontend",
        "file:///workspace/backend",
    ],
)
```

Then test these cases:

1. Two roots.
2. Zero roots.
3. Client without roots support.
4. Dynamic roots callback.
5. Change the workspace during the connection.
6. Attempt a path outside the roots.
7. Log how many times `ctx.list_roots()` causes a protocol round trip.

The goal is to understand why this:

```python
roots = await ctx.list_roots()
```

is much more architecturally significant than it looks.

# Next lesson — Sampling

Roots taught us:

```
SERVER
can ask CLIENT
for environment context
```

**Sampling** takes this much further:

```
SERVER
can ask CLIENT
to use its LLM
```

That introduces:

```
sampling/createMessage
model preferences
system prompts
message context
token limits
human approval
nested inference
agentic loops
trust boundaries
```

It is one of the most important MCP concepts because it separates **who owns the tool/server logic** from **who owns the model invocation**.