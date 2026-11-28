Keeping this **protocol-first, incremental, and hands-on**, with the FastMCP abstraction explicitly peeled back.

# Lesson 7 — Elicitation

**Elicitation** solves this problem:

> A server starts an operation but discovers that it needs information only the user can provide.

Examples:

```
"Which environment should I deploy to?"
"Which customer did you mean?"
"Do you approve deleting these records?"
"What date should the booking use?"
```

The architectural distinction is:

```
Sampling
SERVER → asks CLIENT → ask an LLM

Elicitation
SERVER → asks CLIENT → ask the USER
```

MCP `2026-07-28` supports two elicitation modes: **form mode** for structured in-band input and **URL mode** for sensitive/out-of-band interactions. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

---

## 1. First principle: why not put everything in Tool arguments?

Suppose we define:

```python
book_flight(
    destination: str,
    date: str,
    seat: str,
    meal: str,
    confirm: bool,
)
```

This forces the caller to provide everything before the operation starts.

But real workflows are often conditional:

```
call book_flight()
        │
        ▼
choose destination
        │
        ▼
look up available flights
        │
        ▼
only now ask:
"Which flight?"
        │
        ▼
only then ask:
"Confirm $742 purchase?"
```

The later questions depend on earlier answers.

Elicitation lets you implement **progressive disclosure** instead of creating huge up-front tool schemas. FastMCP explicitly describes missing parameters, clarification, progressive disclosure, and dynamic workflows as core elicitation use cases. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 2. Modern MCP does not pause the Tool

This is the most important concept.

You might imagine:

```
tool starts
   │
   ▼
ask user
   │
   ▼
wait...
   │
   ▼
resume same function
```

That was essentially the older handshake-era model.

MCP `2026-07-28` instead uses **Multi Round-Trip Requests (MRTR)**:

```
CLIENT                            SERVER
  │                                 │
  │──── tools/call ────────────────>│
  │                                 │
  │<── InputRequiredResult ─────────│
  │                                 │
  │   user answers form             │
  │                                 │
  │──── NEW tools/call ────────────>│
  │     + inputResponses            │
  │     + requestState              │
  │                                 │
  │<── final Tool result ───────────│
```

Each round is an independent request. Nothing has to remain blocked waiting for the user. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

Professional phrase:

> **“Modern elicitation is continuation-based rather than coroutine-suspension-based.”**

---

# 3. Raw protocol: first call

Suppose we expose:

```
book_flight()
```

The client initially sends:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "book_flight",
    "arguments": {}
  }
}
```

The server realizes:

```
destination is missing
```

Instead of failing, it returns an `InputRequiredResult`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "destination": {
        "method": "elicitation/create",
        "params": {
          "mode": "form",
          "message": "Where would you like to fly?",
          "requestedSchema": {
            "type": "object",
            "properties": {
              "destination": {
                "type": "string"
              }
            },
            "required": ["destination"]
          }
        }
      }
    }
  }
}
```

In modern MCP, `elicitation/create` is placed inside `InputRequiredResult.inputRequests`; it is not emitted as a server-initiated JSON-RPC request. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

---

# 4. What `requestedSchema` means

The client now knows:

```
message:
"Where would you like to fly?"

expected input:
object containing destination:string
```

A UI could render:

```
┌───────────────────────────────────────┐
│ Where would you like to fly?         │
│                                       │
│ Destination: [ Paris              ]   │
│                                       │
│             [Cancel] [Submit]         │
└───────────────────────────────────────┘
```

The schema is intentionally restricted. Form-mode schemas are flat objects containing primitive values such as strings, numbers/integers, booleans, and enum-style selections; complex nested object structures are intentionally excluded to keep client UIs straightforward. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

---

# 5. Client response

Suppose the user enters:

```
Paris
```

The elicitation result is:

```json
{
  "action": "accept",
  "content": {
    "destination": "Paris"
  }
}
```

MCP defines three actions:

```
accept
decline
cancel
```

`accept` means the user submitted/approved; `decline` means explicit rejection; `cancel` means the interaction was dismissed without an affirmative or negative choice. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

These distinctions matter.

Do not write:

```python
if not answer:
    cancelled()
```

Instead explicitly model:

```
accept
    → continue

decline
    → user deliberately refused

cancel
    → workflow was dismissed/interrupted
```

---

# 6. The client retries the original operation

The response doesn't go to:

```
elicitation/response
```

There is no separate response method.

The client retries:

```
tools/call
```

and attaches the answer:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "book_flight",
    "arguments": {},
    "inputResponses": {
      "destination": {
        "action": "accept",
        "content": {
          "destination": "Paris"
        }
      }
    }
  }
}
```

The new request must have a new JSON-RPC ID because it is an independent request. `inputResponses` keys correspond to the keys the server originally assigned in `inputRequests`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

---

# 7. One logical workflow can therefore execute repeatedly

Suppose the workflow needs destination and date:

```
RUN 1
│
├── destination missing
└── ask destination


RUN 2
│
├── destination = Paris
├── date missing
└── ask date


RUN 3
│
├── destination = Paris
├── date = 2026-08-20
└── return booking
```

So one logical operation is actually:

```
3 separate tool executions
```

This is a major design implication.

Your Tool should be safe to **re-enter from the top**.

Professional term:

> **Guard pattern**

FastMCP uses that term for modern interactive tools: each invocation checks what information is already available, asks for what's missing, or proceeds. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 8. Working FastMCP 4 example

Modern MCP `2026-07-28` support currently lives in **FastMCP 4 beta**. The official installation instructions currently pin the beta as:

```bash
pip install "fastmcp==4.0.0b1"
```

FastMCP recommends exact version pinning for prereleases. [FastMCP](https://gofastmcp.com/getting-started/installation?utm_source=chatgpt.com)

Create:

```
elicitation_demo.py
```

```python
import asyncio

from fastmcp import Client, Context, FastMCP
from fastmcp.client.elicitation import ElicitResult

from mcp.types import (
    ElicitRequest,
    ElicitRequestFormParams,
    InputRequiredResult,
)


mcp = FastMCP("BookingServer")


def ask(
    key: str,
    message: str,
    field: str,
    request_state: str | None = None,
) -> InputRequiredResult:
    """Create one form-mode elicitation request."""

    request = ElicitRequest(
        method="elicitation/create",
        params=ElicitRequestFormParams(
            message=message,
            requested_schema={
                "type": "object",
                "properties": {
                    field: {
                        "type": "string",
                    }
                },
                "required": [field],
            },
        ),
    )

    return InputRequiredResult(
        result_type="input_required",
        input_requests={
            key: request,
        },
        request_state=request_state,
    )


@mcp.tool
async def book_flight(
    ctx: Context,
) -> str | InputRequiredResult:

    responses = ctx.input_responses

    # ROUND 1
    if responses is None:
        return ask(
            key="destination",
            message="Where would you like to fly?",
            field="destination",
        )

    # ROUND 2
    if "destination" in responses:
        answer = responses["destination"]

        if answer.action != "accept":
            return "Booking cancelled."

        destination = answer.content["destination"]

        return ask(
            key="date",
            message=f"When would you like to fly to {destination}?",
            field="date",
            request_state=f"destination={destination}",
        )

    # ROUND 3
    date_answer = responses["date"]

    if date_answer.action != "accept":
        return "Booking cancelled."

    destination = ctx.request_state.split("=", 1)[1]
    date = date_answer.content["date"]

    return f"Booked a flight to {destination} on {date}"


async def elicitation_handler(
    message,
    response_type,
    params,
    context,
):
    """
    Simulated UI/user.

    A real application would show a form here.
    """

    print(f"SERVER ASKS: {message}")

    if "Where" in message:
        return ElicitResult(
            action="accept",
            content=response_type(
                destination="Paris",
            ),
        )

    if "When" in message:
        return ElicitResult(
            action="accept",
            content=response_type(
                date="2026-08-20",
            ),
        )

    return ElicitResult(action="cancel")


async def main():
    async with Client(
        mcp,
        mode="auto",
        elicitation_handler=elicitation_handler,
        input_required_max_rounds=5,
    ) as client:

        result = await client.call_tool(
            "book_flight",
            {},
        )

        print(result.data)


if __name__ == "__main__":
    asyncio.run(main())
```

FastMCP documents this same guard architecture: `ctx.input_responses` contains answers from the previous round, `ctx.request_state` carries continuation information, and `Client` automatically fulfils `InputRequiredResult` requests and retries until a terminal result is reached. [FastMCP](https://gofastmcp.com/servers/elicitation)

Expected interaction:

```
SERVER ASKS: Where would you like to fly?
SERVER ASKS: When would you like to fly to Paris?
Booked a flight to Paris on 2026-08-20
```

---

# 9. What FastMCP abstracted

The client code contains:

```python
await client.call_tool(
    "book_flight",
    {},
)
```

It looks like **one call**.

But FastMCP performs:

```
call_tool
    │
    ▼
tools/call #1
    │
    ▼
InputRequiredResult
    │
    ▼
elicitation_handler
    │
    ▼
tools/call #2
    │
    ▼
InputRequiredResult
    │
    ▼
elicitation_handler
    │
    ▼
tools/call #3
    │
    ▼
final ToolResult
```

FastMCP's client automatically drives these input-required rounds, with a configurable maximum; its current default maximum is 10 rounds. [FastMCP](https://gofastmcp.com/clients/elicitation)

So:

> **`client.call_tool()` is one logical application operation but may represent multiple MCP requests.**

---

# 10. `ctx.input_responses`

This is the modern server's key API.

Initial execution:

```python
ctx.input_responses is None
```

Later:

```python
ctx.input_responses
```

might contain:

```
{
    "destination":
        ElicitResult(...)
}
```

The key:

```
destination
```

comes from:

```python
input_requests={
    "destination": request
}
```

So:

```
inputRequests key
       │
       ▼
client fulfills request
       │
       ▼
inputResponses same key
```

This is **request correlation at the logical-input level**, separate from JSON-RPC IDs. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

---

# 11. `requestState`

Problem:

On round 2 we know:

```
destination = Paris
```

On round 3 we only receive the date response.

Where does `Paris` come from?

We carried it via:

```python
request_state="destination=Paris"
```

Then:

```python
ctx.request_state
```

contains it during the next invocation.

Conceptually:

```
ROUND 2

destination = Paris
      │
      ▼
requestState
      │
      ▼
CLIENT
opaque token
      │
      ▼
ROUND 3
      │
      ▼
ctx.request_state
```

FastMCP 4 seals `request_state` before putting it on the wire and verifies/unseals it when it returns. In horizontally scaled deployments, replicas need shared request-state keys so another worker can validate continuation state created by the first one. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 12. Do not put huge objects in `requestState`

Bad:

```python
request_state = serialize(
    entire_customer_record,
    search_results,
    30MB_document,
    ...
)
```

It traverses the client each round.

Prefer:

```
small continuation information
```

such as:

```
workflow stage
selected ID
small immutable choices
lookup token
```

FastMCP explicitly recommends keeping continuation state small because it round-trips on each leg. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 13. Decline vs cancel is normal control flow

Consider:

```python
answer = responses["destination"]
```

Never immediately do:

```python
destination = answer.content["destination"]
```

First:

```python
if answer.action != "accept":
    ...
```

Because `decline` and `cancel` legitimately have no submitted content. FastMCP specifically warns to inspect `action` before reading `content`; declining is a normal response rather than a protocol error. [FastMCP](https://gofastmcp.com/servers/elicitation)

Architecturally:

```
accept
│
└── workflow continues

decline
│
└── user says "no"

cancel
│
└── interaction abandoned

protocol error
│
└── something malfunctioned
```

These should not be conflated.

---

# 14. Form schemas

Suppose we want:

```
deployment environment
replica count
approval
```

Protocol schema:

```json
{
  "type": "object",
  "properties": {
    "environment": {
      "type": "string",
      "enum": [
        "staging",
        "production"
      ]
    },
    "replicas": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20
    },
    "confirm": {
      "type": "boolean"
    }
  },
  "required": [
    "environment",
    "replicas",
    "confirm"
  ]
}
```

Clients can use this schema both to generate UI controls and validate responses before returning them. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

The professional principle is:

> **Elicitation schemas describe user-interface input contracts, not arbitrary domain-object serialization.**

---

# 15. FastMCP's typed abstraction in the legacy API

FastMCP can generate those schemas from Python types.

For handshake-era MCP:

```python
from dataclasses import dataclass

from fastmcp import Context, FastMCP


mcp = FastMCP("DeployServer")


@dataclass
class Deployment:
    environment: str
    replicas: int


@mcp.tool
async def deploy(ctx: Context) -> str:
    result = await ctx.elicit(
        message="Configure the deployment",
        response_type=Deployment,
    )

    if result.action == "accept":
        config = result.data

        return (
            f"Deploying {config.replicas} replicas "
            f"to {config.environment}"
        )

    if result.action == "decline":
        return "Deployment declined."

    return "Deployment cancelled."
```

Here FastMCP turns the Python response type into an MCP-compatible elicitation schema and reconstructs typed Python data from the client's answer. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 16. But `ctx.elicit()` belongs to the older protocol architecture

This:

```python
result = await ctx.elicit(...)
```

means:

```
tool coroutine
      │
      ▼
elicitation/create
      │
      ▼
client UI
      │
      ▼
user response
      │
      ▼
same coroutine resumes
```

That only works on handshake-era connections through MCP `2025-11-25`.

Modern `2026-07-28` removes that server→client back-channel, so FastMCP requires the guard/`InputRequiredResult` pattern instead. The framework treats the two approaches as strict protocol-era-specific behaviors. [FastMCP](https://gofastmcp.com/servers/elicitation)

So:

```
FastMCP legacy
──────────────
await ctx.elicit()

imperative
pause/resume


FastMCP modern
──────────────
return InputRequiredResult

continuation / guard pattern
re-run from top
```

---

# 17. Form mode must not carry secrets

This is an important security boundary.

Do **not** use normal form elicitation for:

```
password
API key
access token
payment credentials
```

The current MCP specification explicitly prohibits form-mode elicitation for those kinds of sensitive credentials. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

Why?

Because form data passes through:

```
USER
 ↓
MCP CLIENT
 ↓
MCP message
 ↓
SERVER
```

That may expose secrets to:

```
client memory
logs
observability
intermediate systems
model-adjacent application state
```

---

# 18. URL-mode elicitation

For sensitive workflows, MCP provides:

```
mode = "url"
```

Conceptually:

```
MCP server
    │
    │ "Open this secure page"
    ▼
MCP client
    │
    ▼
USER ───── HTTPS ─────> SERVER / THIRD PARTY
```

Example protocol request:

```json
{
  "method": "elicitation/create",
  "params": {
    "mode": "url",
    "url": "https://example.com/connect",
    "message": "Connect your external account to continue."
  }
}
```

The secret never has to travel back through MCP. URL mode is specifically intended for out-of-band sensitive interactions such as third-party authorization, credentials, and payment-style workflows. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

---

# 19. URL mode is not MCP authentication

This distinction is easy to get wrong.

```
MCP Authorization
─────────────────
CLIENT authenticates to MCP SERVER


URL elicitation OAuth
─────────────────────
USER authorizes MCP SERVER
to access some THIRD-PARTY service
```

Example:

```
Chat client
   │
   │ MCP OAuth
   ▼
GitHub-management MCP server
   │
   │ URL elicitation
   ▼
GitHub OAuth
```

The MCP specification explicitly separates the two. URL elicitation must not be used as a replacement for the client's authorization to the MCP server itself. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)

Professional phrase:

> **“URL elicitation is an out-of-band user interaction mechanism, not the MCP authorization protocol.”**

---

# 20. Elicitation can apply to more than Tools

`InputRequiredResult` is not fundamentally a Tool concept.

Modern MCP allows it for:

```
tools/call
resources/read
prompts/get
``` :chatgpt-content-reference{index="21"}


So a resource can say:

```
"You need to select a quarter before I can return this report."
```

And a prompt can say:

```
"I need to know which customer this workflow concerns."
```

FastMCP uses the same `ctx.input_responses` pattern for prompts and resources. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 21. Deeper design rule: Tool argument or Elicitation?

Ask this:

### Known before operation starts?

Use a **Tool argument**.

```python
search_products(
    query: str,
)
```

### Only knowable after execution begins?

Consider **Elicitation**.

```
Search returns 5 candidates.

"Which one did you mean?"
```

### Dangerous action requiring explicit human consent?

Consider **Elicitation**.

```
"Delete 412 production records?"
```

That gives a useful distinction:

```
Tool argument
=
caller input


Elicitation
=
runtime human input
```

---

# 22. Avoid needless elicitation

Bad:

```
Tool:
get_weather(city)

server:
"What city?"
```

when the Tool could simply expose:

```python
get_weather(city: str)
```

Elicitation creates:

```
extra round trips
extra UI
extra latency
more workflow states
more cancellation handling
```

Use it when information is genuinely **runtime-dependent**, not because interactive tools seem sophisticated.

---

# 23. Multi-turn Elicitation is a state machine

Our flight example is really:

```
STATE 0
need destination
       │
       ▼
STATE 1
need date
       │
       ▼
STATE 2
complete
```

That means interactive MCP Tools should often be designed explicitly as **state machines**.

Professional terminology:

```
state
transition
guard
continuation
terminal state
```

A robust implementation can be described as:

> “The tool is a re-entrant state machine whose guards inspect `inputResponses` and continuation state.”

That is much more precise than:

> “The tool asks some follow-up questions.”

---

# 24. Complete abstraction map

| MCP protocol | FastMCP |
|---|---|
| `elicitation/create` | elicitation request object |
| `requestedSchema` | Python types / generated schema or explicit schema |
| `InputRequiredResult` | guard-pattern return |
| `inputRequests` | `InputRequiredResult.input_requests` |
| `inputResponses` | `ctx.input_responses` |
| `requestState` | `ctx.request_state` |
| `accept` | accepted `ElicitResult` |
| `decline` | declined result |
| `cancel` | cancelled result |
| repeated original request | automatically driven by `Client` |
| client UI integration | `elicitation_handler=` |
| legacy nested elicitation | `await ctx.elicit()` |

FastMCP's same client-side `elicitation_handler` can service handshake-style pushed elicitation and modern input-required rounds. [FastMCP](https://gofastmcp.com/clients/elicitation)

---

# 25. Jargon checkpoint

| Term | Meaning |
|---|---|
| **Elicitation** | Server requesting user-provided input |
| **Form mode** | In-band structured input |
| **URL mode** | Out-of-band external interaction |
| **Requested schema** | Expected user-input contract |
| **Progressive disclosure** | Asking only for information when it becomes necessary |
| **Human-in-the-loop** | Explicit user participation in an automated workflow |
| **Guard pattern** | Re-run operation, test available inputs, ask for missing ones |
| **MRTR** | Multi Round-Trip Requests |
| **Continuation state** | State needed to continue a later round |
| **Re-entrant Tool** | Tool safe to execute again as a continuation |
| **Terminal result** | Final result instead of another input request |
| **Out-of-band interaction** | Interaction occurring outside the MCP data channel |
| **Accept / decline / cancel** | Three explicit user response states |

A strong explanation:

> **“Modern MCP elicitation uses MRTR rather than a server back-channel. The server returns an `InputRequiredResult` containing one or more `elicitation/create` requests. The client gathers user input and retries the original operation with correlated `inputResponses`. FastMCP implements this as a guard pattern using `ctx.input_responses` and `ctx.request_state`, while the client automatically drives the rounds through its `elicitation_handler`.”**

---

# Hands-on exercises

Extend the working booking example in this order:

1. Add a third round asking for `seat_class`.
2. Make `seat_class` an enum: `economy`, `business`, `first`.
3. Simulate `decline` during the date step.
4. Simulate `cancel` during confirmation.
5. Add a final explicit boolean confirmation before booking.
6. Set `input_required_max_rounds=2` and observe the protection against an endless interaction loop. FastMCP exposes this client-side limit specifically to prevent nonterminating guards. [FastMCP](https://gofastmcp.com/clients/elicitation)
7. Rewrite the same workflow using legacy `ctx.elicit()` and compare the control flow.
8. Draw the workflow as a state machine before writing any code.

The key test is being able to explain why:

```
Tool argument
      ≠
requestedSchema
      ≠
inputRequests
      ≠
inputResponses
      ≠
requestState
```

They represent different layers of the workflow.

## Next lesson

The next useful block is **MCP protocol utilities**:

```
Progress
Cancellation
Logging
Pagination
Completion
```

We should start with **Progress + Cancellation together**, because they form the control plane for long-running MCP operations.