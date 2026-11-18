# Lesson 14 — FastMCP Middleware and the Request Pipeline

This lesson is mostly **FastMCP architecture**, not a new MCP protocol feature.

At protocol level the client still sends:

```
tools/call
resources/read
prompts/get
tools/list
...
```

FastMCP middleware inserts an interception pipeline **around** those MCP operations:

```
MCP request
    │
    ▼
Middleware A
    │
    ▼
Middleware B
    │
    ▼
Middleware C
    │
    ▼
Tool / Resource / Prompt
    │
    ▼
Middleware C
    │
    ▼
Middleware B
    │
    ▼
Middleware A
    │
    ▼
MCP response
```

FastMCP middleware can inspect requests, call the next handler, modify results, handle errors, or stop processing entirely. [FastMCP](https://gofastmcp.com/servers/middleware?utm_source=chatgpt.com)

---

## 1. First principle: cross-cutting concerns

Suppose you have 50 tools.

Bad architecture:

```python
@mcp.tool
async def tool_a(...):
    authenticate()
    check_rate_limit()
    start_timer()
    log_request()

    try:
        result = do_work()
    except Exception:
        log_error()
        raise

    log_duration()
    return result
```

Then repeat the same structure in:

```
tool_b
tool_c
tool_d
...
```

These behaviors aren't really part of the business operation.

They're **cross-cutting concerns**:

```
authentication
authorization
logging
timing
rate limiting
auditing
error handling
caching
```

Middleware centralizes them.

---

# 2. The middleware contract

The essential shape is:

```python
async def on_something(
    self,
    context,
    call_next,
):
    # before

    result = await call_next(context)

    # after

    return result
```

`call_next(context)` is the critical operation: calling it continues down the pipeline; omitting it short-circuits processing. [FastMCP](https://gofastmcp.com/servers/middleware?utm_source=chatgpt.com)

Think:

```
            BEFORE

Middleware A
    │
    ▼
Middleware B
    │
    ▼
Tool
    │
    ▼
Middleware B
    │
    ▼
Middleware A

             AFTER
```

This pattern is sometimes called an **onion architecture** or **middleware stack**.

---

# 3. Minimal custom middleware

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
)


class TraceMiddleware(Middleware):

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        print(
            "→",
            context.message.name,
        )

        result = await call_next(context)

        print(
            "←",
            context.message.name,
        )

        return result


mcp = FastMCP("MiddlewareDemo")

mcp.add_middleware(
    TraceMiddleware()
)


@mcp.tool
def add(
    a: int,
    b: int,
) -> int:
    return a + b
```

Calling:

```
add(10, 20)
```

conceptually produces:

```
→ add
30
← add
```

The `on_call_tool` hook only targets Tool invocation; FastMCP provides more general and more specific hooks depending on what traffic you need to intercept. [FastMCP](https://gofastmcp.com/servers/middleware?utm_source=chatgpt.com)

---

# 4. Middleware hook hierarchy

FastMCP provides several interception levels.

```
MOST GENERAL

on_message
    │
    ▼
on_request / on_notification
    │
    ▼
operation-specific hook

on_call_tool
on_read_resource
on_get_prompt
...
```

The official middleware model groups hooks into message-level, request/notification-level, and operation-specific hooks. [FastMCP](https://gofastmcp.com/servers/middleware)

Use the narrowest hook that matches the concern.

For example:

```
Measure every MCP request
→ on_request


Audit Tool executions only
→ on_call_tool


Enforce Resource policy
→ on_read_resource
```

---

# 5. Middleware ordering matters

Suppose you register:

```python
mcp.add_middleware(A())
mcp.add_middleware(B())
mcp.add_middleware(C())
```

The execution is:

```
REQUEST

A →
    B →
        C →
            Tool


RESPONSE

            Tool
        ← C
    ← B
← A
```

FastMCP executes middleware in registration order inbound; the first middleware becomes the last one executed on the response path. [FastMCP](https://gofastmcp.com/servers/middleware)

Professional phrase:

> **“Middleware ordering determines the effective policy composition.”**

---

# 6. Why error handling normally goes outside

Suppose:

```
ErrorHandling
    │
    ▼
RateLimit
    │
    ▼
Timing
    │
    ▼
Tool
```

If the Tool fails:

```
Tool
 ↓
exception
 ↓
Timing
 ↓
RateLimit
 ↓
ErrorHandling catches it
```

If error handling instead sits **inside** the other middleware:

```
RateLimit
    │
    ▼
ErrorHandling
```

it cannot catch an exception thrown by `RateLimit` itself.

FastMCP's own production ordering example puts `ErrorHandlingMiddleware` first so that it wraps all later middleware. [FastMCP](https://gofastmcp.com/servers/middleware)

---

# 7. A useful production stack

Official FastMCP examples use a structure like:

```python
from fastmcp import FastMCP

from fastmcp.server.middleware.error_handling import (
    ErrorHandlingMiddleware,
)
from fastmcp.server.middleware.rate_limiting import (
    RateLimitingMiddleware,
)
from fastmcp.server.middleware.timing import (
    TimingMiddleware,
)
from fastmcp.server.middleware.logging import (
    LoggingMiddleware,
)


mcp = FastMCP("ProductionServer")

mcp.add_middleware(
    ErrorHandlingMiddleware()
)

mcp.add_middleware(
    RateLimitingMiddleware(
        max_requests_per_second=50
    )
)

mcp.add_middleware(
    TimingMiddleware()
)

mcp.add_middleware(
    LoggingMiddleware()
)
```

FastMCP documents this ordering explicitly: error handling outside, followed by rate limiting, timing, and logging. [FastMCP](https://gofastmcp.com/servers/middleware)

Conceptually:

```
               REQUEST

Error handling
      │
      ▼
Rate limiting
      │
      ▼
Timing
      │
      ▼
Logging
      │
      ▼
Tool

               RESPONSE

Logging
      │
      ▼
Timing
      │
      ▼
Rate limiting
      │
      ▼
Error handling
```

---

# 8. Pre-processing vs post-processing

Middleware can operate before:

```python
async def on_call_tool(
    self,
    context,
    call_next,
):
    validate_request(context)

    result = await call_next(context)

    return result
```

or after:

```python
async def on_call_tool(
    self,
    context,
    call_next,
):
    result = await call_next(context)

    result = sanitize(result)

    return result
```

Or both:

```python
async def on_call_tool(
    self,
    context,
    call_next,
):
    started = time.perf_counter()

    try:
        return await call_next(context)

    finally:
        duration = (
            time.perf_counter()
            - started
        )

        record(duration)
```

FastMCP explicitly supports request pre-processing, response transformation, early termination, and error interception around `call_next`. [FastMCP](https://gofastmcp.com/servers/middleware?utm_source=chatgpt.com)

---

# 9. Short-circuiting

Middleware does **not** have to call:

```python
await call_next(context)
```

Imagine maintenance mode:

```python
class MaintenanceMiddleware(
    Middleware
):

    async def on_call_tool(
        self,
        context,
        call_next,
    ):
        if MAINTENANCE_MODE:
            raise RuntimeError(
                "Server under maintenance"
            )

        return await call_next(
            context
        )
```

The Tool never executes.

```
request
    │
    ▼
MaintenanceMiddleware
    │
    ├── enabled
    │      └── STOP
    │
    └── disabled
           │
           ▼
         Tool
```

This is known as **short-circuiting the pipeline**.

---

# 10. MiddlewareContext

Middleware needs to know what it is intercepting.

Conceptually, `MiddlewareContext` carries information such as:

```
MCP method
message type
message payload
FastMCP Context
timing/request metadata
```

FastMCP exposes `context.method`, `context.message`, and `context.fastmcp_context`, among other request details. [FastMCP](https://gofastmcp.com/servers/middleware?utm_source=chatgpt.com)

For a Tool call:

```python
async def on_call_tool(
    self,
    context,
    call_next,
):
    print(
        context.message.name
    )

    print(
        context.message.arguments
    )

    return await call_next(context)
```

That gives middleware access to the **protocol-facing invocation**.

---

# 11. Middleware + request state

From the previous lesson:

```
middleware
    │
    ▼
ctx.set_state(...)
    │
    ▼
Tool
    │
    ▼
ctx.get_state(...)
```

Example:

```python
from uuid import uuid4

from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
)


class RequestIdMiddleware(Middleware):

    async def on_request(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        ctx = context.fastmcp_context

        if ctx is not None:
            await ctx.set_state(
                "request_id",
                str(uuid4()),
            )

        return await call_next(context)
```

Then:

```python
from fastmcp import Context
from fastmcp.dependencies import (
    CurrentContext,
)


@mcp.tool
async def operation(
    ctx: Context = CurrentContext(),
):
    return {
        "request_id":
            await ctx.get_state(
                "request_id"
            )
    }
```

FastMCP request state is specifically useful for passing information from middleware to handlers during one request. [FastMCP](https://gofastmcp.com/v2/servers/context?utm_source=chatgpt.com)

---

# 12. Built-in: LoggingMiddleware

FastMCP provides:

```python
from fastmcp.server.middleware.logging import (
    LoggingMiddleware,
    StructuredLoggingMiddleware,
)
```

`LoggingMiddleware` produces human-readable request/response logs; `StructuredLoggingMiddleware` emits structured JSON-style logs suitable for aggregation systems. Payload logging is disabled by default and can be explicitly enabled/truncated. [FastMCP](https://gofastmcp.com/servers/middleware)

Example:

```python
mcp.add_middleware(
    LoggingMiddleware(
        include_payloads=False,
    )
)
```

For production, leaving raw payloads disabled by default is usually the safer posture because MCP arguments may contain sensitive user data.

---

# 13. Built-in: TimingMiddleware

```python
from fastmcp.server.middleware.timing import (
    TimingMiddleware,
)


mcp.add_middleware(
    TimingMiddleware()
)
```

FastMCP's timing middleware measures request execution duration; `DetailedTimingMiddleware` additionally tracks operation-specific timings for Tools, Resources, and Prompts. [FastMCP](https://gofastmcp.com/servers/middleware)

This is a classic cross-cutting concern:

```
Tool A
Tool B
Resource C
Prompt D
      │
      ▼
same timing policy
```

No business component needs its own stopwatch.

---

# 14. Built-in: RateLimitingMiddleware

FastMCP provides two main built-in approaches:

```
RateLimitingMiddleware
→ token bucket

SlidingWindowRateLimitingMiddleware
→ fixed rolling-window accounting
```

The token-bucket implementation supports a sustained request rate plus burst capacity; FastMCP also allows custom client identification. [FastMCP](https://gofastmcp.com/servers/middleware)

Example:

```python
from fastmcp.server.middleware.rate_limiting import (
    RateLimitingMiddleware,
)


mcp.add_middleware(
    RateLimitingMiddleware(
        max_requests_per_second=10.0,
        burst_capacity=20,
    )
)
```

Conceptually:

```
normal load

tokens replenish
      │
      ▼
requests consume tokens


burst

20 immediate requests
      │
      ▼
burst capacity permits them


too many

no tokens
      │
      ▼
reject / throttle
```

---

# 15. Rate limiting requires an identity decision

Ask:

> **Who is being rate limited?**

Possible keys:

```
IP address
authenticated user
OAuth client
tenant
API key
global server
```

A global limiter can let one noisy client starve every other user.

FastMCP exposes a `get_client_id` callback specifically so rate-limit identity can be customized. [FastMCP](https://gofastmcp.com/servers/middleware)

Professional vocabulary:

> **Rate-limit key**

or:

> **quota principal**

---

# 16. Built-in: ResponseCachingMiddleware

FastMCP can cache:

```
Tool calls
Resource reads
list operations
Prompt retrieval
```

with configurable TTL and include/exclude rules. [FastMCP](https://gofastmcp.com/servers/middleware)

Example:

```python
from fastmcp.server.middleware.caching import (
    ResponseCachingMiddleware,
    CallToolSettings,
)


mcp.add_middleware(
    ResponseCachingMiddleware(
        call_tool_settings=
            CallToolSettings(
                included_tools=[
                    "expensive_report"
                ],
                ttl=60,
            )
    )
)
```

Then:

```
first call

expensive_report(x)
      │
      ▼
actual Tool
      │
      ▼
cache result


second identical call
within TTL
      │
      ▼
cache hit
      │
      └── Tool may not execute
```

This is **response memoization**.

---

# 17. Critical cache-security trap

FastMCP's default cache key is based on:

```
operation name
+
arguments
```

and **does not include user or session identity**. The official documentation explicitly warns that user-specific results derived from auth context can therefore be unsafe to cache unless caching is disabled or identity is incorporated appropriately. [FastMCP](https://gofastmcp.com/servers/middleware)

Imagine:

```python
@mcp.tool
async def my_profile(
    token=CurrentAccessToken(),
):
    return lookup_user(
        token.claims["sub"]
    )
```

The Tool arguments are:

```
{}
```

Alice calls:

```
my_profile({})
```

cache stores:

```
Alice's profile
```

Bob calls:

```
my_profile({})
```

Same cache key.

Potential outcome:

```
Bob receives Alice's data
```

That is a serious security bug.

---

# 18. General caching rule

Before caching a Tool ask:

```
Does output depend ONLY on explicit arguments?
```

Safe-ish example:

```python
calculate_tax(
    amount=100,
    rate=0.08,
)
```

Potentially dangerous:

```python
my_profile()
```

because output depends on:

```
authenticated identity
```

Also dangerous:

```python
current_balance(account_id)
```

if data changes frequently and your TTL does not match required freshness.

Cache correctness depends on:

```
cache key
TTL
identity
authorization
data freshness
side effects
```

not merely performance.

---

# 19. Never cache mutating Tool calls indiscriminately

Consider:

```python
charge_card(
    amount=100
)
```

If a response cache intercepts an identical second request:

```
request 1
→ card charged
→ result cached


request 2
→ cached response
→ card NOT charged
```

The external semantics changed completely.

Therefore caching is usually appropriate for:

```
pure/read-only
deterministic
expensive
reasonably stable
```

operations.

Not:

```
create
delete
send
charge
increment
```

This is an application-design inference rather than an MCP protocol rule, but it follows directly from how response caching skips underlying execution.

---

# 20. Built-in: RetryMiddleware

FastMCP provides:

```python
from fastmcp.server.middleware.error_handling import (
    RetryMiddleware,
)


mcp.add_middleware(
    RetryMiddleware(
        max_retries=3,
        retry_exceptions=(
            ConnectionError,
            TimeoutError,
        ),
    )
)
```

The middleware retries configured transient exceptions with exponential backoff. [FastMCP](https://gofastmcp.com/servers/middleware)

Conceptually:

```
Tool attempt
    │
    ▼
TimeoutError
    │
    ▼
backoff
    │
    ▼
Tool attempt 2
```

---

# 21. Retry + side effects is dangerous

Suppose:

```python
send_payment()
```

does this:

```
call payment provider
      │
      ▼
payment succeeds
      │
      ▼
network response lost
      │
      ▼
TimeoutError
```

RetryMiddleware sees:

```
timeout
```

and calls the Tool again.

Potential result:

```
payment #1
payment #2
```

This is why retries must be designed together with:

```
idempotency
idempotency keys
transaction boundaries
safe retry classifications
```

Professional phrase:

> **“Retries are safe only when failure ambiguity and idempotency are understood.”**

---

# 22. Built-in: ErrorHandlingMiddleware

FastMCP's `ErrorHandlingMiddleware` centralizes exception logging/transformation and supports optional tracebacks and callbacks. [FastMCP](https://gofastmcp.com/servers/middleware)

Example:

```python
from fastmcp.server.middleware.error_handling import (
    ErrorHandlingMiddleware,
)


mcp.add_middleware(
    ErrorHandlingMiddleware(
        include_traceback=False,
        transform_errors=True,
    )
)
```

This keeps Tool code focused on:

```
business failure
```

rather than repeatedly implementing:

```
log unexpected exception
convert error
attach diagnostics
```

---

# 23. Built-in: ResponseLimitingMiddleware

LLM context windows make response size a real architectural constraint.

FastMCP provides:

```python
from fastmcp.server.middleware.response_limiting import (
    ResponseLimitingMiddleware,
)


mcp.add_middleware(
    ResponseLimitingMiddleware(
        max_size=500_000
    )
)
```

The built-in middleware truncates oversized Tool responses according to the configured limit. [FastMCP](https://gofastmcp.com/servers/middleware)

This protects:

```
server memory
network bandwidth
client memory
LLM context
```

But truncation can also damage structured output semantics, so for APIs where complete structured data is required, designing pagination/resources is usually preferable to relying on truncation.

---

# 24. Middleware mutation

Middleware can modify requests before execution.

Conceptually:

```python
async def on_call_tool(
    self,
    context,
    call_next,
):
    context.message.arguments[
        "tenant_id"
    ] = resolve_tenant()

    return await call_next(context)
```

But this should make you cautious.

You've now transformed:

```
client-visible contract
```

into:

```
hidden argument injection
```

Dependency injection or request state is usually clearer for infrastructure-owned values.

Use middleware mutation when it is genuinely protocol-level transformation, not just because it is technically possible.

---

# 25. Middleware response transformation

Likewise:

```python
async def on_call_tool(
    self,
    context,
    call_next,
):
    result = await call_next(context)

    return sanitize(result)
```

This can support:

```
redaction
standard envelopes
response limiting
policy filtering
```

But remember:

```
Tool declares outputSchema
```

If middleware changes the result into something incompatible with that schema, you've broken the MCP contract.

Professional rule:

> **Post-processing must preserve declared component contracts.**

---

# 26. Middleware vs decorators

Suppose one Tool needs admin permission:

```python
@mcp.tool(
    auth=require_scopes("admin")
)
def reset_system():
    ...
```

That's **component policy**.

Suppose every Tool needs:

```
api:access
```

That's better as:

```python
AuthMiddleware(...)
```

FastMCP explicitly supports both global authorization middleware and per-component authorization, with both requirements applying when combined. [FastMCP](https://gofastmcp.com/servers/authorization?utm_source=chatgpt.com)

Think:

```
ONE COMPONENT
→ decorator/component auth


ALL REQUESTS
→ middleware
```

---

# 27. Middleware vs Dependency Injection

From the previous lesson:

```
MIDDLEWARE
horizontal pipeline concern


DEPENDENCY
handler requirement
```

Examples:

```
Middleware:
rate limit
audit
request ID
timing
global auth


Dependency:
database
repository
HTTP client
tenant service
current token
```

A common architecture:

```
request
  │
  ▼
Middleware
  │
  ├── authenticate
  ├── establish request ID
  └── timing
  │
  ▼
Dependency graph
  │
  ├── DB connection
  └── domain service
  │
  ▼
Tool
```

They complement each other.

---

# 28. Middleware vs MCP protocol

This distinction should now be explicit:

```
MCP PROTOCOL

tools/call
resources/read
prompts/get
JSON-RPC
schemas
results


FASTMCP MIDDLEWARE

Python interception layer
around processing those messages
```

A remote MCP client does not know whether your server uses:

```
0 middleware
5 middleware
100 middleware
```

unless that middleware changes externally observable behavior.

That's implementation encapsulation.

---

# 29. Full request walkthrough

Suppose the client calls:

```
generate_report(customer_id=42)
```

With:

```
ErrorHandling
RateLimit
Audit
Timing
Cache
```

The request travels:

```
CLIENT

tools/call
    │
    ▼
ErrorHandling
    │
    ▼
RateLimit
    │
    ├── over quota?
    │      └── STOP
    │
    ▼
Audit
    │
    └── record start
    │
    ▼
Timing
    │
    └── timer start
    │
    ▼
Cache
    │
    ├── HIT
    │    └── return cached response
    │
    └── MISS
         │
         ▼
       Tool
         │
         ▼
    domain service
         │
         ▼
       result
         │
         ▼
Cache stores result
         │
         ▼
Timing records latency
         │
         ▼
Audit records success
         │
         ▼
ErrorHandling returns
         │
         ▼
CLIENT
```

Notice an important consequence:

> On a cache hit, middleware *inside* the cache layer may never execute.

This is why ordering affects metrics and auditing semantics.

---

# 30. Cache ordering thought experiment

Compare:

```
Timing
  │
  ▼
Cache
  │
  ▼
Tool
```

versus:

```
Cache
  │
  ▼
Timing
  │
  ▼
Tool
```

### Timing outside cache

Measures:

```
all requests
including cache hits
```

### Timing inside cache

Measures:

```
only operations that reach underlying execution
```

Neither is automatically right.

You must decide what your metric means.

Professional phrase:

> **“Middleware position defines the measurement boundary.”**

---

# 31. Audit ordering

For audit trails, you often want:

```
Audit OUTSIDE cache
```

because:

```
cached access
is still access
```

Otherwise a user could repeatedly retrieve cached sensitive information and your audit layer might never see it.

This is a useful security-design principle:

```
performance optimization
must not bypass
security/audit policy
```

---

# 32. Rate limiting and cache ordering

Another design choice:

```
RateLimit
   │
   ▼
Cache
```

means:

```
cache hits still count toward quota
```

Whereas:

```
Cache
   │
   ▼
RateLimit
```

could allow cache hits to bypass rate limiting.

Usually the first is safer for abuse prevention, though exact policy depends on what the quota represents.

Again:

> **Ordering is policy.**

---

# 33. Middleware and mounted servers

FastMCP supports parent/child server composition.

Its middleware hierarchy is:

```
parent middleware
      │
      ▼
child middleware
      │
      ▼
child component
```

Parent middleware runs for requests routed into mounted child servers; child middleware applies only within that child. FastMCP also notes that request/session state does not automatically cross mount boundaries unless configured appropriately. [FastMCP](https://gofastmcp.com/servers/middleware)

This matters for:

```
global authentication
tenant routing
central audit
```

which often belongs on the parent.

---

# 34. A working custom middleware stack

```python
import time
from uuid import uuid4

from fastmcp import FastMCP
from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
)


class RequestIdMiddleware(Middleware):

    async def on_request(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        ctx = context.fastmcp_context

        if ctx:
            await ctx.set_state(
                "request_id",
                str(uuid4()),
            )

        return await call_next(context)


class ToolTimingMiddleware(Middleware):

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        started = time.perf_counter()

        try:
            return await call_next(context)

        finally:
            elapsed_ms = (
                time.perf_counter()
                - started
            ) * 1000

            print(
                f"{context.message.name}: "
                f"{elapsed_ms:.2f}ms"
            )


mcp = FastMCP("PipelineDemo")

mcp.add_middleware(
    RequestIdMiddleware()
)

mcp.add_middleware(
    ToolTimingMiddleware()
)


@mcp.tool
async def add(
    a: int,
    b: int,
) -> int:
    return a + b
```

Now mentally execute:

```
tools/call
    │
    ▼
RequestIdMiddleware
    │
    ▼
ToolTimingMiddleware
    │
    ▼
add()
    │
    ▼
ToolTimingMiddleware finally
    │
    ▼
RequestIdMiddleware
    │
    ▼
CallToolResult
```

---

# 35. Professional vocabulary

| Term | Meaning |
|---|---|
| **Middleware** | Interception layer around request processing |
| **Pipeline** | Ordered middleware execution chain |
| **Cross-cutting concern** | Behavior applying across many components |
| **Pre-processing** | Logic before underlying operation |
| **Post-processing** | Logic after operation returns |
| **Short-circuit** | Stop processing without calling downstream handler |
| **`call_next`** | Continue to next middleware/handler |
| **Onion model** | Nested inbound/outbound middleware execution |
| **Measurement boundary** | Portion of pipeline included in timing/metrics |
| **Rate-limit key** | Identity against which quota is enforced |
| **Token bucket** | Rate-limit algorithm supporting bursts |
| **Sliding window** | Rate limit based on requests in recent time interval |
| **Response cache** | Stored result reused for equivalent requests |
| **Cache key** | Value identifying reusable cached result |
| **TTL** | Time-to-live before cache expiration |
| **Retry policy** | Rules controlling re-execution after failure |
| **Exponential backoff** | Increasing delay between retries |
| **Idempotency** | Repetition doesn't add unintended effects |
| **Response transformation** | Middleware modification of downstream output |

A strong explanation:

> **“FastMCP middleware is an implementation-level interception pipeline around MCP operations. Middleware executes in registration order inbound and reverse order outbound, with `call_next()` defining whether the pipeline continues. I use middleware for cross-cutting concerns such as auth, rate limiting, timing, auditing, error handling, and caching, while preserving domain dependencies in DI. Ordering is itself policy—for example, audit should generally wrap caching so cache hits remain visible, and response caching must not leak user-specific results because FastMCP's default cache keys are based on operation name and arguments rather than authenticated identity.”** [FastMCP](https://gofastmcp.com/servers/middleware)

---

# Hands-on assignment

Build one Tool:

```
expensive_lookup(customer_id)
```

and add these middleware one at a time:

1. Request ID.
2. Timing.
3. Logging.
4. Rate limiting.
5. Response caching.
6. Error handling.
7. Retry handling.
8. Response limiting.

Then deliberately change the order and observe:

```
Timing outside cache
vs
Timing inside cache

Audit outside cache
vs
Audit inside cache

Rate limit outside cache
vs
Rate limit inside cache
```

Next, create:

```
my_profile()
```

whose result comes from authenticated identity rather than Tool arguments, enable `ResponseCachingMiddleware`, and explain why that is unsafe with the default cache-key strategy. FastMCP explicitly warns about this identity omission. [FastMCP](https://gofastmcp.com/servers/middleware)

The conceptual test:

```
middleware
    ≠
dependency
    ≠
Tool logic
    ≠
MCP protocol
    ≠
transport
```

They sit at different layers.

## Next lesson — Server Composition: Providers, Mounting, Proxies, and Transforms

Next we should move into the features that make FastMCP much more than a decorator framework:

```
Providers
    → where components come from

Mounting
    → combine MCP servers

Proxy
    → expose another MCP server through yours

Transforms
    → rename/filter/rewrite components

Tool Search
    → expose large tool catalogs efficiently

composition boundaries
namespaces
authorization inheritance
middleware interaction
```

This is where we'll start building **MCP gateways and composed servers**, rather than single standalone servers.