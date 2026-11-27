# Lesson 15 — Server Composition: Providers, Mounting, Proxies, Transforms, Tool Search

This lesson is primarily a **FastMCP abstraction layer**.

At the MCP protocol level, the client still only sees things such as:

```
tools/list
tools/call
resources/list
resources/read
prompts/list
prompts/get
```

There is no wire-level concept called:

```
Provider
Mount
ProxyProvider
Transform
ToolSearchTransform
```

Those are FastMCP mechanisms for deciding **where MCP components come from and what clients ultimately see**. This is an architectural inference from the MCP server primitives and FastMCP's provider model. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts?utm_source=chatgpt.com)

The mental model:

```
                         FastMCP Server

                              │
                ┌─────────────┼─────────────┐
                │             │             │
             Provider      Provider      Provider
                │             │             │
              local         mounted        remote
                │             │             │
                └──────┬──────┴──────┬──────┘
                       │             │
                    Transforms       │
                       │             │
                       └──────┬──────┘
                              ▼
                         MCP components
                              │
                    tools/resources/prompts
                              │
                              ▼
                          MCP client
```

---

# 1. First principle: what is a Provider?

Previously:

```python
@mcp.tool
def add(a: int, b: int) -> int:
    return a + b
```

You probably imagined:

```
FastMCP
  │
  └── stores tool
```

More precisely, FastMCP's decorators add components to a:

```
LocalProvider
```

A **provider** is simply a source of:

```
Tools
Resources
Prompts
```

When a client asks `tools/list`, FastMCP queries its providers and combines the resulting components. When a particular Tool is called, FastMCP resolves which provider owns it and delegates execution there. [FastMCP](https://gofastmcp.com/servers/providers/overview)

So:

```
@mcp.tool
      │
      ▼
LocalProvider
      │
      ▼
FastMCP
```

You were already using providers without naming them.

Professional phrasing:

> **“Providers separate component sourcing from protocol exposure.”**

---

# 2. Why providers exist

Imagine one server eventually needs capabilities from:

```
your Python code
another internal FastMCP module
remote billing MCP
remote GitHub MCP
database-generated tools
OpenAPI-generated tools
```

Without abstraction:

```
FastMCP Server
│
├── weird local registry
├── custom remote forwarding
├── imported functions
├── generated tools
└── special cases everywhere
```

With providers:

```
FastMCP Server
│
├── LocalProvider
├── FastMCPProvider
├── ProxyProvider
└── custom Provider
```

Everything downstream can treat the resulting objects uniformly as MCP components. FastMCP explicitly designed providers to support composition, remote proxies, and dynamic component sources. [FastMCP](https://gofastmcp.com/servers/providers/overview)

---

# Part A — Mounting

## 3. Mounting means composing FastMCP servers

Suppose teams own separate modules.

```python
from fastmcp import FastMCP


weather = FastMCP("Weather")
calendar = FastMCP("Calendar")


@weather.tool
def get_forecast(city: str) -> str:
    return f"Forecast for {city}"


@calendar.tool
def get_events(date: str) -> str:
    return f"Events for {date}"
```

You could expose them as two MCP endpoints.

Or create one:

```python
main = FastMCP("CompanyGateway")

main.mount(
    weather,
    namespace="weather",
)

main.mount(
    calendar,
    namespace="calendar",
)
```

The client sees:

```
weather_get_forecast
calendar_get_events
```

FastMCP implements mounted servers through `FastMCPProvider`; namespacing is applied automatically to avoid collisions. [FastMCP](https://gofastmcp.com/servers/providers/overview)

---

# 4. Protocol-level view of mounting

The client has no idea that there are two internal servers.

It sends:

```json
{
  "method": "tools/list"
}
```

and receives conceptually:

```json
{
  "tools": [
    {
      "name": "weather_get_forecast"
    },
    {
      "name": "calendar_get_events"
    }
  ]
}
```

Later:

```json
{
  "method": "tools/call",
  "params": {
    "name": "weather_get_forecast",
    "arguments": {
      "city": "Phoenix"
    }
  }
}
```

Internally:

```
tools/call
    │
    ▼
main FastMCP
    │
    ▼
resolve provider
    │
    ▼
weather provider
    │
    ▼
get_forecast()
```

This is a useful abstraction boundary:

> **Mounting changes server implementation topology without changing MCP semantics.**

---

# 5. Why namespace matters

Imagine both servers define:

```
get_data
```

Without namespacing:

```
Weather:
get_data

Calendar:
get_data

         ↓

collision
```

With:

```python
main.mount(
    weather,
    namespace="weather",
)

main.mount(
    calendar,
    namespace="calendar",
)
```

you get:

```
weather_get_data
calendar_get_data
```

Namespacing applies to other component identities too. FastMCP documents Tool and Prompt prefixes and inserts the namespace into Resource/Resource Template URIs. [FastMCP](https://gofastmcp.com/servers/composition)

Professional term:

> **namespace collision avoidance**

---

# 6. Mounting is a live composition link

This is different from copying components once.

```python
main.mount(
    weather,
    namespace="weather",
)
```

Then later:

```python
@weather.tool
def get_alerts(city: str) -> str:
    return f"Alerts for {city}"
```

The new Tool becomes visible through `main` as well. FastMCP describes `mount()` as a live link rather than a one-time component copy. [FastMCP](https://gofastmcp.com/servers/composition)

Think:

```
COPY

child ─── snapshot ───> parent


MOUNT

child <───────────────> parent
        live source
```

---

# Part B — Proxying

## 7. Mount and Proxy solve different topologies

Mounting usually starts with:

```
FastMCP Python object
inside your application
```

Proxying starts with:

```
another MCP server
accessible through a Client
```

Example architecture:

```
                 Your Gateway MCP
                       │
          ┌────────────┴────────────┐
          │                         │
      local Tools             ProxyProvider
                                    │
                                    ▼
                           remote MCP server
```

FastMCP's `ProxyProvider` sources Tools, Resources, and Prompts from another MCP server through a client connection. [FastMCP](https://gofastmcp.com/servers/providers/proxy)

---

# 8. Working proxy example

Suppose a remote MCP service exists at:

```
https://backend.example.com/mcp
```

Create:

```python
from fastmcp.server import create_proxy


proxy = create_proxy(
    "https://backend.example.com/mcp",
    name="BackendProxy",
)


if __name__ == "__main__":
    proxy.run()
```

Your local server now exposes components obtained from the remote MCP server. FastMCP documents `create_proxy()` as accepting URLs, file paths, and transport configurations. [FastMCP](https://gofastmcp.com/servers/providers/proxy)

The topology:

```
MCP Client
    │
    │ stdio perhaps
    ▼
FastMCP Proxy
    │
    │ HTTP perhaps
    ▼
Remote MCP server
```

This is **transport bridging**.

---

# 9. Peel the Proxy abstraction

Client calls:

```
tools/list
```

Your proxy roughly does:

```
client
  │
  │ tools/list
  ▼
proxy server
  │
  │ upstream client.list_tools()
  ▼
remote server
  │
  │ tools list
  ▼
proxy
  │
  ▼
client
```

Invocation similarly becomes:

```
original client
     │
     │ tools/call("search")
     ▼
proxy
     │
     │ upstream tools/call("search")
     ▼
backend
     │
     ▼
ToolResult
     │
     ▼
proxy
     │
     ▼
original client
```

FastMCP's proxy connects upstream lazily during proxy initialization and subsequently forwards MCP operations through its upstream client. [FastMCP](https://gofastmcp.com/servers/providers/proxy)

---

# 10. Proxy use cases

The main patterns are:

```
TRANSPORT BRIDGE

HTTP backend
     ↓
stdio frontend


AGGREGATION

Server A ─┐
Server B ─┼── Gateway
Server C ─┘


SECURITY GATEWAY

public client
     ↓
authenticated FastMCP gateway
     ↓
private MCP backend


STABLE FACADE

clients
   ↓
gateway URL
   ↓
backend implementation can change
```

These are explicit FastMCP ProxyProvider use cases. [FastMCP](https://gofastmcp.com/servers/providers/proxy)

---

# 11. Proxying does not magically make the backend safe

Suppose upstream exposes:

```
delete_production_database
```

Proxying it means you are potentially exposing that capability too.

You still need:

```
authorization
visibility filtering
tool transformation
rate limits
auditing
```

A proxy is a **routing/composition mechanism**, not a security policy.

This is why FastMCP's gateway pattern becomes more powerful when combined with the middleware/auth lessons we've already covered.

---

# Part C — Transforms

## 12. What problem does a Transform solve?

Imagine you proxy an external server exposing:

```
very_long_enterprise_internal_search_database_v2
```

You don't control its code.

But your clients should see:

```
search
```

You need:

```
original component
       │
       ▼
transformation layer
       │
       ▼
client-facing component
```

FastMCP calls this a:

```
Transform
```

Transforms modify components as they flow from providers toward clients. [FastMCP](https://gofastmcp.com/servers/transforms/transforms)

---

# 13. Provider vs Transform

These concepts should be very clear:

```
PROVIDER
"Where does this component come from?"


TRANSFORM
"What should this component look like?"
```

Example:

```
ProxyProvider
      │
      │ tool:
      │ verbose_internal_data_fetcher
      ▼
ToolTransform
      │
      ▼
search
```

Professional phrase:

> **“Providers source capabilities; transforms adapt their exposed contract.”**

---

# 14. Working ToolTransform example

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import (
    ToolTransform,
)
from fastmcp.tools.tool_transform import (
    ToolTransformConfig,
)


mcp = FastMCP("TransformDemo")


@mcp.tool
def verbose_internal_data_fetcher(
    query: str,
) -> str:
    """Fetch data from the internal database."""

    return f"Results for: {query}"


mcp.add_transform(
    ToolTransform({
        "verbose_internal_data_fetcher":
            ToolTransformConfig(
                name="search",
                description=(
                    "Search the internal database."
                ),
            )
    })
)
```

The implementation remains:

```
verbose_internal_data_fetcher
```

but `tools/list` exposes:

```
search
```

FastMCP's `ToolTransform` can rename tools, change descriptions, tags, and reshape argument schemas without modifying the source Tool. [FastMCP](https://gofastmcp.com/servers/transforms/tool-transformation)

---

# 15. Reverse mapping during execution

Renaming is not merely cosmetic.

Client calls:

```
search
```

FastMCP must map that back to:

```
verbose_internal_data_fetcher
```

Conceptually:

```
DISCOVERY

provider
verbose_internal_data_fetcher
        │
        ▼
ToolTransform
        │
        ▼
search
        │
        ▼
client


INVOCATION

client
search
        │
        ▼
ToolTransform reverse lookup
        │
        ▼
verbose_internal_data_fetcher
        │
        ▼
provider
```

FastMCP's transform pipeline explicitly reverses these mappings when resolving client-facing component names. [FastMCP](https://gofastmcp.com/servers/transforms/transforms)

This is why transforms are more than presentation decorators.

---

# 16. Provider-level vs server-level transforms

You can transform just one provider:

```
Backend provider
     │
     └── Namespace("backend")
```

while leaving local Tools unchanged.

Or transform everything:

```
Provider A ─┐
Provider B ─┼── server transform → Client
Provider C ─┘
```

FastMCP runs provider-level transforms first, then server-level transforms. [FastMCP](https://gofastmcp.com/servers/transforms/transforms)

Use provider-level transforms when:

```
"Only this backend needs adaptation."
```

Use server transforms when:

```
"This policy applies to the entire exposed API."
```

---

# 17. Namespace itself is a Transform

Earlier we wrote:

```python
main.mount(
    weather,
    namespace="weather",
)
```

Internally, this is effectively adding a namespace transform to that mounted provider. FastMCP explicitly implements mount namespacing using transforms. [FastMCP](https://gofastmcp.com/servers/providers/overview)

So:

```
mount(namespace="weather")
```

is convenience syntax over the more general transformation architecture.

That is a useful framework insight.

---

# Part D — Building a Gateway

## 18. Combine local + mounted + proxied components

Imagine:

```
                         Company MCP Gateway
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
             LOCAL             MOUNTED             PROXY
               │                  │                  │
       company_status()       Finance MCP        Git MCP
                                  │                  │
                            Namespace           Namespace
                              finance              git
```

Implementation sketch:

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy


main = FastMCP("CompanyGateway")


@main.tool
def company_status() -> str:
    return "Operational"


finance = FastMCP("Finance")


@finance.tool
def revenue_report() -> str:
    return "Revenue report"


main.mount(
    finance,
    namespace="finance",
)


git_proxy = create_proxy(
    "https://git.example.com/mcp",
    name="GitBackend",
)


main.mount(
    git_proxy,
    namespace="git",
)
```

Client may see conceptually:

```
company_status
finance_revenue_report
git_search_repositories
git_create_issue
...
```

The client still sees one MCP server.

---

# 19. Gateway vs Aggregator

These terms are often used loosely.

A useful distinction:

```
AGGREGATOR

primary goal:
combine capabilities


GATEWAY

combine capabilities
+
policy enforcement
+
stable frontend
+
auth
+
observability
+
routing/transformation
```

A FastMCP server containing:

```
ProxyProviders
Transforms
AuthMiddleware
AuditMiddleware
RateLimitingMiddleware
```

is much closer to an **MCP gateway**.

---

# Part E — Tool Search

## 20. The large-catalog problem

Suppose your gateway aggregates:

```
Sales MCP          60 tools
Git MCP            80 tools
AWS MCP           140 tools
Finance MCP        70 tools
Internal MCP       150 tools
```

Total:

```
500 tools
```

Sending all 500 schemas into an LLM's available-tool context can create:

```
large context consumption
poor tool selection
higher latency
semantic confusion
```

FastMCP's Tool Search transforms solve this by replacing the advertised large catalog with synthetic discovery tools. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)

---

# 21. Tool Search mental model

Without Tool Search:

```
tools/list

tool_1
tool_2
tool_3
...
tool_500
```

With Tool Search:

```
tools/list

search_tools
call_tool
```

Then the model can:

```
search_tools("email")
```

and receive relevant candidate Tools.

After discovering:

```
send_email
search_email
get_email_thread
```

it can invoke one through:

```
call_tool(
    name="send_email",
    arguments={...}
)
```

FastMCP's search transform hides the original tools from normal listing while keeping them callable; `call_tool` is a synthetic proxy Tool for models that only know about advertised tools. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)

---

# 22. Important protocol insight

Tool Search is **not a new MCP protocol primitive**.

At wire level:

```
search_tools
```

is just an ordinary:

```
MCP Tool
```

and:

```
call_tool
```

is another ordinary:

```
MCP Tool
```

So the protocol still sees:

```
tools/list
tools/call
```

FastMCP has built a **discovery protocol on top of MCP Tools**.

This is a powerful design pattern:

> **Higher-level behavior can be composed out of ordinary MCP primitives without extending the wire protocol.**

---

# 23. Working Tool Search example

```python
from fastmcp import FastMCP

from fastmcp.server.transforms.search import (
    RegexSearchTransform,
)


mcp = FastMCP("LargeCatalog")


@mcp.tool
def search_database(
    query: str,
) -> str:
    """Search the company database."""

    return f"Database results: {query}"


@mcp.tool
def send_email(
    recipient: str,
    body: str,
) -> str:
    """Send an email message."""

    return f"Sent to {recipient}"


@mcp.tool
def lookup_invoice(
    invoice_id: str,
) -> str:
    """Look up an invoice."""

    return invoice_id


mcp.add_transform(
    RegexSearchTransform()
)
```

Now `tools/list` primarily exposes synthetic search/call tooling instead of the entire underlying catalog. The default search result limit is five, and FastMCP also offers BM25-based search for ranked relevance. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)

---

# 24. Search then call

Conceptual interaction:

```
MODEL
 │
 │ tools/call
 │ search_tools(query="email")
 ▼

RESULT

send_email
  description: Send an email message
  inputs:
    recipient
    body


MODEL
 │
 │ tools/call
 │ call_tool(
 │   name="send_email",
 │   arguments={...}
 │ )
 ▼

FastMCP
 │
 ▼
normal Tool pipeline
 │
 ├── transforms
 ├── authorization
 ├── middleware
 ▼
send_email()
```

FastMCP's `call_tool` proxy resolves the target through the normal Tool pipeline rather than bypassing transforms and middleware. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)

That detail matters for security.

---

# 25. Tool Search is discovery, not access control

The underlying Tools are hidden from:

```
tools/list
```

but they remain callable.

Therefore:

```
not listed
≠
not executable
```

Tool Search controls **discovery**, not authorization. FastMCP explicitly states that the original tools remain callable after being hidden from the listing. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)

So don't say:

```
"Admin tool is secure because Tool Search hides it."
```

Wrong.

Use actual authorization/visibility controls.

---

# 26. Search respects authorization

FastMCP's Tool Search queries through the normal visibility and authorization pipeline, so Tools removed through component auth, visibility transforms, or middleware filtering do not appear in search results. The proxy Tool also follows the same execution boundary. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)

Correct architecture:

```
all internal tools
       │
       ▼
authorization
       │
       ▼
visibility
       │
       ▼
Tool Search
       │
       ▼
user-visible discoveries
```

Security filtering should happen before exposing search results.

---

# 27. Pin important Tools

Some Tools should remain visible without search:

```
help
status
search_tools
call_tool
```

FastMCP supports:

```python
mcp.add_transform(
    RegexSearchTransform(
        always_visible=[
            "help",
            "status",
        ]
    )
)
```

Pinned tools stay in `tools/list` and are excluded from search-result duplication. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)

This is useful for a small **control surface** plus a large searchable catalog.

---

# 28. Composition and latency

Suppose:

```
gateway
 │
 ├── local provider       1 ms
 ├── remote provider    300 ms
 ├── remote provider    500 ms
 └── remote provider    200 ms
```

A discovery request that queries all providers can inherit the latency of those sources.

FastMCP warns that parent listing performance is affected by mounted server performance, especially HTTP-backed sources and deep mounting hierarchies. [FastMCP](https://gofastmcp.com/servers/composition)

Professional term:

> **fan-out latency**

Architecture:

```
client request
     │
     ├── backend A
     ├── backend B
     └── backend C
           │
           ▼
wait / aggregate
```

Composition creates operational coupling.

---

# 29. Composition creates failure domains

Suppose:

```
Finance backend DOWN
```

Should:

```
Git tools
Calendar tools
Local tools
```

also become unavailable?

That depends on your gateway design.

You need to think about:

```
timeouts
partial discovery
cache
circuit breakers
health status
retry policy
backend isolation
```

This is no longer merely an MCP question.

It is **distributed-systems architecture**.

---

# 30. Provider resolution conflicts

Suppose two providers expose:

```
search
```

FastMCP needs to choose.

Current provider resolution prefers the highest matching component version; for equal/unversioned components, provider registration order breaks ties, with `LocalProvider` registered first. [FastMCP](https://gofastmcp.com/servers/providers/overview)

But relying on collision priority is usually weaker design than using explicit namespaces:

```
sales_search
git_search
```

Professional principle:

> **Prefer explicit namespaces over accidental provider precedence.**

---

# 31. Full architectural example

You can now build something like:

```
                      CORPORATE MCP GATEWAY

                               │
                       AuthMiddleware
                               │
                        AuditMiddleware
                               │
                    ┌──────────┼──────────┐
                    │          │          │
                 Local     Finance      GitHub
                Provider    Mount        Proxy
                    │          │          │
                    │      Namespace   Namespace
                    │          │          │
                    └──────────┼──────────┘
                               │
                         Visibility
                               │
                         ToolTransform
                               │
                          Tool Search
                               │
                               ▼
                          MCP CLIENT

                         visible tools:

                            status
                         search_tools
                           call_tool
```

At wire level, it is still just:

```
tools/list
tools/call
resources/read
prompts/get
```

That is the key design achievement.

---

# 32. Provider vs Middleware vs Transform

This is an important interview distinction.

```
PROVIDER
────────
Where components COME FROM.

Examples:
local
mounted
remote MCP


TRANSFORM
─────────
What components LOOK LIKE
when exposed.

Examples:
namespace
rename
visibility
tool search


MIDDLEWARE
──────────
What happens while
REQUESTS are processed.

Examples:
auth
rate limiting
audit
timing
```

And:

```
DEPENDENCY INJECTION
────────────────────
What implementation services
a handler needs.

Examples:
database
repository
HTTP client
```

Four different layers.

---

# 33. Protocol → FastMCP map

| Goal | MCP wire | FastMCP |
|---|---|---|
| Local component | normal Tool/Resource/Prompt | `LocalProvider` |
| Compose local server | unchanged MCP listing/calls | `mount()` / `FastMCPProvider` |
| Remote federation | unchanged MCP operations | `ProxyProvider` |
| Avoid name conflicts | client sees renamed identifiers | `Namespace` |
| Rewrite Tool contract | client sees modified Tool | `ToolTransform` |
| Hide capability | removed from discovery | visibility transforms/auth |
| Large Tool catalog | ordinary synthetic Tools | Tool Search transform |
| Execute searched Tool | ordinary `tools/call` | synthetic `call_tool` proxy |

---

# 34. Professional vocabulary

Know these precisely:

| Term | Meaning |
|---|---|
| **Provider** | Source of MCP components |
| **LocalProvider** | Provider backing decorators/local registration |
| **FastMCPProvider** | Provider wrapping another FastMCP server |
| **ProxyProvider** | Provider sourcing components through an MCP client |
| **Mounting** | Live composition of another FastMCP server |
| **Federation** | Exposing multiple independent systems through one interface |
| **Aggregation** | Combining multiple capability sources |
| **Gateway** | Controlled frontend for one/multiple backends |
| **Namespace** | Prefix/scope preventing identity collisions |
| **Transform** | Layer modifying component exposure |
| **Reverse mapping** | Mapping client-facing transformed names back to source names |
| **Transport bridging** | Proxy between different transport bindings |
| **Fan-out** | One request querying multiple backends |
| **Tool Search** | On-demand discovery of a large Tool catalog |
| **Synthetic Tool** | Framework-generated Tool implementing higher-level behavior |
| **Capability enumeration** | Discovering what actions a server exposes |

A strong explanation:

> **“FastMCP separates component sourcing from exposure. Providers source Tools, Resources, and Prompts; mounts wrap another FastMCP server through a `FastMCPProvider`, while proxies source components from remote MCP servers through a `ProxyProvider`. Transforms then adapt those components—namespacing, renaming, filtering, or replacing large Tool listings with Tool Search. None of these are additional MCP primitives: clients still interact through standard `tools/list`, `tools/call`, `resources/read`, and `prompts/get` operations.”** [FastMCP](https://gofastmcp.com/servers/providers/overview)

---

# Hands-on assignment

Build a gateway with:

```
LOCAL
status()

MOUNTED
Finance server
  revenue()
  expenses()

PROXIED
another MCP server

TRANSFORMS
finance namespace
remote namespace
rename one verbose Tool

TOOL SEARCH
hide large catalog
pin status()
```

Then verify:

1. `tools/list` from each child independently.
2. `tools/list` from the gateway.
3. Namespace collision handling.
4. Add a Tool to the child **after** mounting and verify it appears.
5. Rename a mounted Tool using `ToolTransform`.
6. Search for that renamed Tool.
7. Call it through `call_tool`.
8. Call the underlying Tool directly and observe that Tool Search hides discovery rather than execution.
9. Put authorization on one Tool and verify it is absent from search for unauthorized callers. FastMCP's Tool Search respects the full authorization/visibility pipeline. [FastMCP](https://gofastmcp.com/servers/transforms/tool-search)
10. Shut down one proxied backend and observe which gateway operations are affected.

The conceptual test:

```
Provider
    ≠
Mount
    ≠
Proxy
    ≠
Transform
    ≠
Middleware
    ≠
Tool Search
    ≠
MCP protocol
```

They solve different architectural problems.

## Next lesson — Versioning, Compatibility, and Capability Negotiation

The next lesson should connect several earlier corrections and protocol eras:

```
MCP version negotiation
2025-11-25 vs 2026-07-28
handshake-era vs stateless-era

FastMCP mode="auto"
backward compatibility
component versioning

feature detection
capabilities
graceful degradation
migration strategy
```

This is essential before deployment because a production MCP server cannot assume every client implements the same protocol revision or optional features.