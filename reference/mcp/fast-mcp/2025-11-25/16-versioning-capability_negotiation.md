# Lesson 16 — Versioning, Compatibility, and Capability Negotiation

This lesson prevents a common MCP mistake:

> **Protocol version, feature capability, FastMCP package version, and Tool/component version are four different things.**

Keep them separate:

```
MCP protocol version
    → which wire contract are we speaking?

Capabilities
    → which optional features can this peer use?

FastMCP version
    → which framework implementation is installed?

Component version
    → which version of this Tool/Resource/Prompt is exposed?
```

The current published MCP docs include the modern `2026-07-28` protocol architecture; the previous `2025-11-25` generation uses the initialization-handshake architecture. FastMCP 4 is designed to serve and consume both eras. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/architecture?utm_source=chatgpt.com)

---

## 1. First principle: version negotiation exists because peers evolve independently

Imagine:

```
MCP Client
version support:
2026-07-28

MCP Server
version support:
2025-11-25
```

You cannot safely assume:

```
latest client
+
older server
=
latest protocol
```

Likewise:

```
new server
+
old client
```

doesn't mean the client magically understands new protocol fields.

Interoperability therefore needs:

```
discover
        │
        ▼
agree on protocol behavior
        │
        ▼
discover capabilities
        │
        ▼
only use supported features
```

Professional phrase:

> **“Protocol versioning establishes syntax and semantics; capability negotiation establishes usable features.”**

---

# 2. There are currently two important MCP eras

Think in terms of architectural eras rather than memorizing dates only.

## Handshake era

Includes `2025-11-25` and earlier:

```
CLIENT                       SERVER
  │                            │
  │──── initialize ───────────>│
  │                            │
  │<── InitializeResult ───────│
  │                            │
  │── initialized ────────────>│
  │                            │
  │      session exists        │
```

Initialization establishes:

```
protocolVersion
client capabilities
server capabilities
client identity
server identity
```

The client proposes a protocol version. If supported, the server returns it; otherwise the server can return another version it supports. If the client cannot support that returned version, it should disconnect. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle?utm_source=chatgpt.com)

---

## Modern era — `2026-07-28`

The architecture becomes:

```
CLIENT                         SERVER
  │                              │
  │──── server/discover ────────>│
  │                              │
  │<── server capabilities ──────│
  │                              │
  │──── tools/call ─────────────>│
  │     client capabilities      │
  │     included per request     │
```

There is no mandatory session-opening `initialize` round trip. Each request carries the client's capabilities under `_meta`, while the server can advertise its capabilities through `server/discover`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/architecture?utm_source=chatgpt.com)

The architectural difference is large:

```
HANDSHAKE ERA

negotiate once
        │
        ▼
session
        │
        ▼
many operations


MODERN ERA

discover server
        │
        ▼
each request
carries required client context
```

---

# 3. Protocol version negotiation — legacy wire level

A `2025-11-25` client sends:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "sampling": {},
      "elicitation": {}
    },
    "clientInfo": {
      "name": "ExampleClient",
      "version": "1.0.0"
    }
  }
}
```

Suppose server supports it:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    },
    "serverInfo": {
      "name": "ExampleServer",
      "version": "2.0.0"
    }
  }
}
```

Then:

```
negotiated protocol
=
2025-11-25
```

The legacy specification explicitly defines this negotiation during initialization. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle?utm_source=chatgpt.com)

---

# 4. What happens if the server doesn't support the requested version?

Suppose:

```
client requests:
2025-11-25


server only supports:
2025-06-18
```

The server may answer:

```json
{
  "protocolVersion": "2025-06-18"
}
```

Now:

```
client supports 2025-06-18?
       │
       ├── yes
       │    └── continue
       │
       └── no
            └── disconnect
```

This is **version fallback**.

Professional terminology:

- protocol negotiation
- compatibility range
- downgrade
- unsupported-version failure

---

# 5. HTTP carries the negotiated version too

In handshake-era Streamable HTTP, after negotiation the client sends:

```http
MCP-Protocol-Version: 2025-11-25
```

on subsequent HTTP requests. An unsupported/invalid protocol-version header must be rejected. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports?utm_source=chatgpt.com)

So there are two different contexts:

```
initialize
    │
    └── negotiates version


HTTP header
    │
    └── identifies version
        used by subsequent request
```

Do not confuse those.

---

# 6. Modern protocol: capabilities become request-oriented

In the modern architecture, every request can contain client capabilities:

```json
{
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion":
        "2026-07-28",

      "io.modelcontextprotocol/clientCapabilities": {
        "elicitation": {}
      }
    }
  }
}
```

This matters because the server should decide behavior based on **what this request's client supports**. Modern MCP describes capability negotiation as per-request client declarations plus server capability discovery. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/architecture?utm_source=chatgpt.com)

Conceptually:

```
REQUEST A

client supports:
elicitation


REQUEST B

client supports:
elicitation
tasks


REQUEST C

client supports:
neither
```

A stateless server doesn't have to remember these capabilities between requests.

---

# 7. Version detection is not enough

This is wrong:

```python
if protocol_version >= "2026-07-28":
    use_feature_x()
```

Why?

Because a protocol version can permit a feature without the peer actually advertising support for it.

Correct mental model:

```
PROTOCOL VERSION

"Can this feature exist in this protocol?"


CAPABILITY

"Did this peer say it supports the feature?"
```

For example, legacy sampling requires the client to advertise:

```json
{
  "sampling": {}
}
```

and sampling with Tool support requires the additional `tools` sampling capability. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling?utm_source=chatgpt.com)

Professional phrase:

> **“Gate optional behavior on negotiated capability, not merely protocol revision.”**

---

# 8. Capability negotiation is feature negotiation

Imagine:

```
SERVER

supports:
tools
resources
prompts


CLIENT

supports:
elicitation
```

That does **not** imply:

```
sampling
roots
tasks
logging
subscriptions
```

Each optional capability is independently meaningful.

Think:

```
protocol version
        │
        ▼
available vocabulary
        │
        ▼
capabilities
        │
        ▼
features actually usable
```

---

# 9. Graceful degradation

Suppose your ideal workflow uses elicitation:

```
Tool
 │
 ├── ask user for missing destination
 │
 ▼
continue
```

What if the client doesn't support it?

Bad:

```
crash
```

Better designs include:

```
A. require destination as Tool argument

B. return an actionable Tool error

C. use elicitation only when available

D. expose separate simple/interactive variants
```

This is **graceful degradation**.

Professional phrase:

> **“Optional MCP capabilities should enhance the workflow rather than accidentally become undocumented hard dependencies.”**

Unless the capability is deliberately mandatory.

---

# 10. Capability requirements should be explicit in architecture

Suppose you build:

```
workspace_analyzer
```

that fundamentally requires client Roots on legacy MCP.

Then document:

```
Required client capability:
roots
```

not:

```
"It works with MCP."
```

“MCP compatible” does not mean:

```
supports every optional capability
```

This is similar to browsers:

```
supports HTTP
    ≠
supports every browser API
```

---

# 11. FastMCP's `mode="auto"`

This is where FastMCP hides much of the complexity.

Current FastMCP clients default to:

```python
from fastmcp import Client


client = Client(
    "https://example.com/mcp",
    mode="auto",
)
```

FastMCP:

```
connect
   │
   ▼
probe server/discover
   │
   ├── modern evidence?
   │      │
   │      └── use modern protocol
   │
   └── no
          │
          └── fall back to
              legacy initialize
```

FastMCP documents `mode="auto"` as the default exactly for mixed fleets of modern and handshake-era MCP servers. [FastMCP](https://gofastmcp.com/clients/client?utm_source=chatgpt.com)

Professional phrase:

> **“FastMCP performs protocol-era negotiation, not just version-string comparison.”**

---

# 12. Working FastMCP negotiation example

```python
import asyncio

from fastmcp import Client


async def main():
    async with Client(
        "http://127.0.0.1:8000/mcp",
        mode="auto",
    ) as client:

        print(
            "Protocol:",
            client.protocol_version,
        )

        print(
            "Server:",
            client.server_info,
        )

        print(
            "Capabilities:",
            client.server_capabilities,
        )

        print(
            "Instructions:",
            client.instructions,
        )


asyncio.run(main())
```

FastMCP provides these properties regardless of whether the metadata came from a legacy `InitializeResult` or modern `DiscoverResult`. [FastMCP](https://gofastmcp.com/clients/client?utm_source=chatgpt.com)

That is a strong abstraction:

```
legacy
InitializeResult
       │
       ┐
       │
       ▼
FastMCP unified properties
       ▲
       │
       ┘
modern
DiscoverResult
```

---

# 13. Force legacy behavior

Sometimes you need the old session model.

```python
client = Client(
    "https://example.com/mcp",
    mode="legacy",
)
```

This forces:

```
initialize
    │
    ▼
handshake/session
```

FastMCP recommends this when you specifically need handshake-era behavior such as the old server back-channel. [FastMCP](https://gofastmcp.com/clients/client?utm_source=chatgpt.com)

Examples include older:

```
ctx.sample()
ctx.list_roots()
ctx.elicit()
```

style interactions.

---

# 14. Pin a modern protocol explicitly

You can also request:

```python
client = Client(
    "https://example.com/mcp",
    mode="2026-07-28",
)
```

FastMCP then adopts that modern version directly instead of probing/falling back. [FastMCP](https://gofastmcp.com/clients/client?utm_source=chatgpt.com)

Use this only when you actually require that protocol.

For general clients:

```
mode="auto"
```

is safer.

Why?

Because explicit version pinning says:

> **“Compatibility with older peers is not acceptable.”**

That's a stronger contract.

---

# 15. FastMCP server supports both eras

FastMCP 4 servers can accept both:

```
old client
   │
   └── initialize
          │
          ▼
      legacy path


new client
   │
   └── server/discover
          │
          ▼
      modern path
```

from the same server deployment. FastMCP explicitly documents dual-era support. [FastMCP](https://gofastmcp.com/more/faq?utm_source=chatgpt.com)

Architecture:

```
                         FastMCP 4 server
                               │
                  ┌────────────┴────────────┐
                  │                         │
             legacy adapter            modern adapter
                  │                         │
             handshake                   stateless
                  │                         │
                  └────────────┬────────────┘
                               ▼
                         same components
```

That is **protocol adaptation**.

---

# 16. Inspect the current request's protocol era

Inside a FastMCP server, the request context exposes the protocol version.

Conceptually:

```python
@mcp.tool
async def protocol_info(
    ctx: Context,
) -> str:
    return str(
        ctx.request_context.protocol_version
    )
```

FastMCP documents `ctx.request_context.protocol_version` for determining which era handled a particular request. [FastMCP](https://gofastmcp.com/more/faq?utm_source=chatgpt.com)

Use this sparingly.

Bad architecture:

```python
if version == ...
    duplicate entire Tool implementation
```

Better:

```
shared domain logic
      │
      ├── legacy interaction adapter
      └── modern interaction adapter
```

Protocol-version branches should stay near the protocol boundary.

---

# 17. Compatibility adapter pattern

Suppose your business logic is:

```python
async def create_booking(
    destination: str,
    date: str,
):
    ...
```

Keep that independent.

Then:

```
LEGACY ADAPTER

ctx.elicit()
      │
      ▼
create_booking()


MODERN ADAPTER

InputRequiredResult / MRTR
      │
      ▼
create_booking()
```

The business service doesn't care which MCP era delivered its inputs.

Professional phrase:

> **“Isolate protocol compatibility logic from domain logic.”**

---

# 18. Backward-compatible parsing

Modern `2026-07-28` results have:

```
resultType
```

But older protocol results did not.

The modern schema explicitly requires clients receiving an earlier result without `resultType` to interpret it as:

```
complete
```

for backward compatibility. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema?utm_source=chatgpt.com)

So:

```
modern result

{
  resultType: "complete",
  ...
}


legacy result

{
  ...
}

modern-compatible interpretation:

resultType = complete
```

This is a classic:

> **compatibility default**

---

# 19. Additive evolution is easier than breaking evolution

Suppose version 1 result:

```json
{
  "name": "Alice"
}
```

Version 2 adds:

```json
{
  "name": "Alice",
  "timezone": "UTC"
}
```

Clients that ignore unknown fields may remain compatible.

Much more dangerous:

```
rename name → full_name
```

because older clients rely on:

```
name
```

General API principle:

```
adding optional fields
      usually easier

changing meaning/type/removing fields
      usually breaking
```

This principle applies to MCP Tool schemas too.

---

# 20. Tool schema compatibility

Suppose v1:

```python
@mcp.tool
def search(
    query: str,
):
```

Then you change to:

```python
@mcp.tool
def search(
    query: str,
    tenant: str,
):
```

You just made `tenant` required.

Old callers sending:

```json
{
  "query": "invoice"
}
```

now fail.

That's a **breaking contract change**.

Safer:

```python
@mcp.tool
def search(
    query: str,
    tenant: str | None = None,
):
```

if a reasonable compatibility behavior exists.

---

# 21. Protocol version vs Component version

Now a completely different kind of versioning.

Suppose:

```
MCP protocol:
2026-07-28
```

but your Tool API has:

```
search version 1
search version 2
```

Those are unrelated.

```
PROTOCOL VERSION

How peers communicate.


COMPONENT VERSION

Which version of an application capability exists.
```

FastMCP supports multiple versions of the same Tool, Resource, or Prompt under one logical identifier. [FastMCP](https://gofastmcp.com/servers/versioning?utm_source=chatgpt.com)

---

# 22. FastMCP Component Versioning

Conceptually:

```python
@mcp.tool(
    version="1.0"
)
def search(
    query: str,
) -> dict:
    ...


@mcp.tool(
    version="2.0"
)
def search(
    query: str,
    limit: int = 10,
) -> dict:
    ...
```

FastMCP can register both versions. By default, clients see the highest version unless transforms/provider filtering select otherwise. [FastMCP](https://gofastmcp.com/servers/versioning?utm_source=chatgpt.com)

So internally:

```
search
│
├── 1.0
└── 2.0
```

client may see:

```
search → 2.0
```

This enables controlled API migration.

---

# 23. Why version the component instead of changing it in place?

Suppose v1 users depend on:

```
search(query)
```

but v2 needs:

```
search(
    query,
    filters,
    ranking_strategy
)
```

Instead of breaking everyone:

```
v1
stays available


v2
introduced separately


migration period


v1 eventually retired
```

Professional terminology:

- parallel versioning
- migration window
- deprecation period
- compatibility window

---

# 24. Component versions should be meaningful, not decorative

Bad:

```
v1
v2
v3
v4
v5
```

every time you edit a description.

Version when the **consumer-facing contract** materially changes.

Examples:

```
input semantics change

output schema changes incompatibly

behavioral guarantees change

old callers would misbehave
```

Not necessarily:

```
internal SQL query optimized
bug fixed
documentation wording improved
```

---

# 25. Semantic versioning vocabulary

A common convention:

```
MAJOR.MINOR.PATCH
```

For example:

```
2.3.1
```

Conceptually:

```
MAJOR
breaking contract change

MINOR
backward-compatible capability addition

PATCH
backward-compatible bug fix
```

FastMCP provides version-comparison utilities and range filtering for component versions. [FastMCP](https://gofastmcp.com/python-sdk/fastmcp-utilities-versions?utm_source=chatgpt.com)

Do not confuse this with MCP's date-based protocol versions:

```
2026-07-28
```

Different versioning schemes.

---

# 26. Component filtering by version

Imagine a gateway exposes:

```
search 1.0
search 2.0
search 3.0-beta
```

One client-facing server might expose:

```
>=2.0 and <3.0
```

while another compatibility endpoint exposes:

```
1.x
```

FastMCP's provider/transform system can filter components by version ranges. [FastMCP](https://gofastmcp.com/python-sdk/fastmcp-utilities-versions?utm_source=chatgpt.com)

This is another reason Providers + Transforms mattered in the previous lesson.

---

# 27. Feature lifecycle matters too

Protocol features themselves can have states such as:

```
Active
Deprecated
Removed
```

The 2026 protocol governance introduces a feature lifecycle intended to give deprecation time before removal. [Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/?utm_source=chatgpt.com)

That means you should not build architecture around:

```
"Feature exists today,
therefore it exists forever."
```

We already saw this with:

```
legacy Roots back-channel
Sampling
MCP Logging
```

Protocol features evolve.

---

# 28. Deprecated ≠ removed

Important terminology:

```
ACTIVE

recommended and supported


DEPRECATED

still supported
but should not be chosen for new designs


REMOVED

no longer part of the protocol
```

A common mistake is saying:

```
"Sampling is deprecated,
so sampling requests are invalid."
```

Not necessarily.

Deprecation means:

```
compatibility may remain
```

but new architecture should move elsewhere.

---

# 29. Capability negotiation beats user-agent detection

Bad:

```python
if client_name == "SomeIDE":
    use_elicitation()
```

Why?

Because:

```
SomeIDE 1.0
may not support it

SomeIDE 2.0
might

another client
might support it perfectly
```

Better:

```
Does client advertise
the required capability?
```

This is called:

> **feature detection**

instead of:

> **client sniffing**

Same principle as web development:

```
detect capability
not brand
```

---

# 30. Build a compatibility matrix

For production, explicitly maintain something like:

| Feature | Legacy | Modern | Required? | Fallback |
|---|---:|---:|---:|---|
| Basic Tools | ✓ | ✓ | yes | none |
| Resources | ✓ | ✓ | optional | Tool fallback |
| Prompt workflows | ✓ | ✓ | optional | client prompt |
| Legacy server sampling | ✓ | no back-channel | no | direct provider |
| Legacy roots request | ✓ | changed architecture | no | explicit input |
| Elicitation | pushed | MRTR | optional | explicit Tool args |
| Progress | ✓ | ✓ | optional | final result only |
| Logging | legacy | deprecated model | no | OTEL/server logs |
| Tasks | version-dependent | modern | optional | synchronous call |

This forces you to decide:

```
what is core
what is enhancement
what happens when absent
```

That's much stronger than hoping negotiation works.

---

# 31. Minimum supported protocol

A production service should eventually decide:

```
What is the oldest protocol era
we will intentionally support?
```

Supporting every historical behavior indefinitely creates:

```
more code paths
more security surface
more testing
more failure modes
slower evolution
```

Compatibility has a cost.

Professional phrase:

> **“Backward compatibility is a product decision with ongoing operational cost.”**

---

# 32. Test both eras

If your FastMCP server claims compatibility with both, test both.

```python
import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_modern(server_url):
    async with Client(
        server_url,
        mode="2026-07-28",
    ) as client:

        result = await client.call_tool(
            "add",
            {
                "a": 1,
                "b": 2,
            },
        )

        assert result.data == 3


@pytest.mark.asyncio
async def test_legacy(server_url):
    async with Client(
        server_url,
        mode="legacy",
    ) as client:

        result = await client.call_tool(
            "add",
            {
                "a": 1,
                "b": 2,
            },
        )

        assert result.data == 3
```

The exact external behavior should remain the same where the protocol feature exists in both eras. FastMCP explicitly supports testing both paths from the same server. [FastMCP](https://gofastmcp.com/more/faq?utm_source=chatgpt.com)

---

# 33. Compatibility testing matrix

Do not test only:

```
new client
+
new server
```

Ideally test:

```
                     SERVER

                legacy      modern

CLIENT legacy      ✓           ✓*

CLIENT modern      ✓           ✓
```

Where supported.

And separately test:

```
feature absent
feature present
feature malformed
feature declined
```

For optional capabilities.

This is **compatibility matrix testing**.

---

# 34. FastMCP package version is another layer

Suppose your environment has:

```
FastMCP 4.x beta
```

That tells you what Python framework code you're using.

It does **not** mean:

```
every connection speaks MCP 4
```

There is no:

```
"MCP version 4"
```

relationship.

FastMCP 4 can speak multiple MCP protocol eras. [FastMCP](https://gofastmcp.com/more/faq?utm_source=chatgpt.com)

So:

```
FastMCP 4
      ≠
MCP protocol v4
```

Important professional correction.

---

# 35. Four independent version axes

You may have a real production system like:

```
FastMCP package
4.0.0b1

MCP protocol
2026-07-28

Tool:
search
2.3.0

Your server application
7.14.2
```

Each means something different.

```
FRAMEWORK VERSION
implementation dependency


PROTOCOL VERSION
wire contract


COMPONENT VERSION
MCP capability contract


APPLICATION VERSION
your deployment/release
```

Do not conflate them in logs, dashboards, or bug reports.

---

# 36. A good production log line

Instead of:

```
Version: 4
```

record:

```json
{
  "application_version": "7.14.2",
  "fastmcp_version": "4.0.0b1",
  "mcp_protocol_version": "2026-07-28",
  "tool": "search",
  "tool_version": "2.3.0"
}
```

Now an incident can answer:

```
Which deployment?

Which framework?

Which protocol path?

Which Tool contract?
```

That is useful observability.

---

# 37. Complete mental model

```
                         CLIENT CONNECTS
                               │
                               ▼
                        protocol era?
                               │
                ┌──────────────┴──────────────┐
                │                             │
             legacy                        modern
                │                             │
            initialize                  server/discover
                │                             │
                └──────────────┬──────────────┘
                               ▼
                       protocol version
                               │
                               ▼
                        capabilities
                               │
                               ▼
                     usable feature set
                               │
                               ▼
                     tools/resources/prompts
                               │
                               ▼
                     component versioning
                               │
                               ▼
                         application logic
```

That hierarchy matters.

---

# 38. Protocol → FastMCP map

| Concern | Protocol level | FastMCP |
|---|---|---|
| Legacy negotiation | `initialize` | `mode="legacy"` |
| Modern discovery | `server/discover` | `mode="auto"` |
| Modern version pin | protocol metadata | `mode="2026-07-28"` |
| Current version | negotiated protocol | `client.protocol_version` |
| Server capabilities | initialize/discover result | `client.server_capabilities` |
| Request protocol version | request context | `ctx.request_context.protocol_version` |
| Optional feature | capability declaration | framework feature detection |
| Backward compatibility | protocol rules | dual-era adapters |
| Tool API migration | not protocol-versioning | component `version=` |
| Component selection | application concern | version transforms/providers |

---

# 39. Professional vocabulary

Know these precisely:

| Term | Meaning |
|---|---|
| **Protocol version** | Revision of MCP's wire contract |
| **Negotiation** | Agreeing on compatible behavior/version |
| **Capability** | Declared optional feature support |
| **Feature detection** | Testing capabilities rather than client identity |
| **Handshake era** | MCP architecture based on `initialize` sessions |
| **Modern/sessionless era** | Per-request MCP architecture starting with `2026-07-28` |
| **Downgrade** | Falling back to an older supported protocol |
| **Graceful degradation** | Continuing with reduced functionality |
| **Backward compatibility** | New implementation still handles older peers |
| **Forward compatibility** | Older implementation tolerates newer compatible structures |
| **Compatibility default** | Defined behavior for missing older fields |
| **Component version** | Version of Tool/Resource/Prompt contract |
| **Compatibility matrix** | Tested combinations of versions/features |
| **Deprecation** | Supported but discouraged for new use |
| **Removal** | Feature no longer supported |
| **Migration window** | Period where old and new contracts coexist |

A strong professional explanation:

> **“MCP has protocol versions and independently negotiated capabilities. In the handshake era, the client proposes a version and both peers exchange capabilities through `initialize`. In the modern `2026-07-28` architecture, the client discovers the server through `server/discover` and supplies client capabilities per request. FastMCP's default `mode="auto"` negotiates between these eras, while component versioning is a separate application-level mechanism for maintaining multiple Tool, Resource, or Prompt contracts.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/architecture?utm_source=chatgpt.com)

---

# Hands-on assignment

Build one FastMCP server with:

```
Tool:
add

Tool:
search version 1.0

Tool:
search version 2.0
```

Then test:

1. Connect with `mode="auto"`.
2. Print `client.protocol_version`.
3. Print `client.server_capabilities`.
4. Connect with `mode="legacy"`.
5. Compare the same `add()` Tool behavior.
6. If your server supports the modern path, connect with `mode="2026-07-28"`.
7. Inside a Tool, inspect `ctx.request_context.protocol_version`.
8. Create one feature that is optional and implement a fallback when unavailable.
9. Register two versions of `search`.
10. Verify which component version FastMCP exposes by default.
11. Introduce a breaking required parameter and observe why it deserves a new component version.
12. Write a compatibility matrix for your server.

The key test is explaining why:

```
FastMCP version
      ≠
MCP protocol version
      ≠
capability
      ≠
component version
      ≠
application version
```

## Next lesson — Testing MCP Correctly

Next we should cover **testing**, because we've accumulated enough layers that manual LLM testing is no longer reliable:

```
unit tests
in-memory FastMCP tests
protocol contract tests
raw MCP assertions
stdio integration tests
HTTP integration tests
auth tests
capability matrices
middleware tests
concurrency tests
failure injection
snapshot/schema tests
```

The central principle will be:

> **Do not test an MCP server by asking an LLM whether it “seems to work.” Test its deterministic protocol contract directly.**