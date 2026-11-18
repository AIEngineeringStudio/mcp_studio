Understood: **concise, structured, verified against official sources, and hands-on**. I’ll teach the engineering reasoning explicitly—what problem we are solving, what design choice follows, then the implementation and professional terminology.

# MCP Elicitation — Course plan

We’ll build this incrementally:

1. **Mental model** — Host vs Client vs Server vs Tool vs Elicitation
2. **Minimal MCP server** with Python + `uv` + FastMCP
3. **First elicitation** without hiding the protocol mechanics
4. **Client-side elicitation handler**
5. **JSON Schema / typed elicitation**
6. `accept` / `decline` / `cancel`
7. **Multi-round elicitation**
8. `InputRequiredResult`, `inputResponses`, `requestState`
9. Guard-pattern design
10. State, idempotency, retries, and side effects
11. HTTP transport and multiple replicas
12. Security and trust boundaries
13. Production architecture
14. Finally: implement the same thing close to the **raw MCP wire protocol** so FastMCP no longer feels magical.

There is one major version issue to understand before writing code.

## 0. The important 2026 change

The current MCP specification is **2026-07-28**. It fundamentally changed how elicitation works.

Older tutorials show this:

```python
result = await ctx.elicit(...)
```

That represents the older **handshake-era** protocol.

Under MCP `2026-07-28`, the server cannot keep a tool execution suspended while calling back into the client. Instead:

```text
client
  |
  | tools/call
  v
server/tool
  |
  | needs user input
  v
InputRequiredResult
  |
  | resultType = input_required
  v
client
  |
  | asks user
  |
  | tools/call + inputResponses
  v
server/tool runs again
```

FastMCP calls the modern implementation the **guard pattern**. Each tool invocation completes. The client obtains the requested input and makes another complete invocation. [FastMCP](https://gofastmcp.com/servers/elicitation)

That distinction is important professionally:

> **Modern MCP elicitation is not a suspended function waiting for user input. It is a stateless multi-round request/response workflow.**

---

# 1. First principles: what problem does elicitation solve?

Imagine an MCP tool:

```python
deploy_service(environment="production")
```

During execution it discovers:

```text
Estimated change:
- 4 instances replaced
- 2 minutes downtime
- production environment
```

The tool should **not blindly continue**.

It needs a decision from the human:

```text
Proceed with this deployment?
```

You have three architectural choices.

### Option A — Tool parameter

```python
deploy_service(
    environment="production",
    approved=True,
)
```

Bad when the user cannot make an informed decision until the tool has calculated something.

### Option B — Return an ordinary response

```text
Deployment requires confirmation.
```

Then the LLM/user has to manually call another tool.

Possible, but you've invented your own interaction protocol.

### Option C — MCP elicitation

The server formally declares:

> I cannot complete this request yet. I require structured input from the client/user.

That is the problem elicitation solves.

---

# 2. Vocabulary

Use these terms precisely:

| Term | Meaning |
|---|---|
| **Host** | User-facing application containing the MCP client |
| **MCP client** | Protocol participant communicating with an MCP server |
| **MCP server** | Exposes tools/resources/etc. |
| **Tool** | Callable capability exposed by the server |
| **Elicitation** | Request for structured user input |
| **Form-mode elicitation** | Structured information collected through the client |
| **Schema** | Contract describing valid input |
| **MRTR** | Multi Round-Trip Request |
| **InputRequiredResult** | Server result saying additional client input is required |
| **inputResponses** | Answers supplied on the subsequent request |
| **requestState** | Opaque state carried between rounds |
| **Guard pattern** | Tool re-runs and checks whether required answers already exist |
| **Request-scoped state** | Data belonging to one request/round |
| **Stateless server** | Server does not need a persistent protocol session between rounds |

A good sentence in an engineering discussion would be:

> “The tool uses an MRTR guard: the first invocation returns an `InputRequiredResult`, and the client replays the tool call with the elicitation result in `inputResponses`.”

That is precise terminology.

---

# 3. Our learning environment

There is another current-version issue.

As of today, the official FastMCP documentation says:

- FastMCP **3.x** is the latest stable version.
- FastMCP **4.0.0b1** is currently prerelease.
- FastMCP 4 builds on MCP Python SDK v2 and supports the new protocol architecture we're studying. [FastMCP](https://gofastmcp.com/getting-started/installation)

So for this course, I recommend deliberately using:

```text
FastMCP 4.0.0b1
MCP SDK 2.x
MCP protocol 2026-07-28
```

Using stable FastMCP 3.x would teach you an architecture that MCP has just moved away from.

---

# 4. Create the lab

```bash
mkdir mcp-elicitation-lab
cd mcp-elicitation-lab

uv init
```

Because FastMCP 4 is currently prerelease, FastMCP's official `uv` instructions require explicitly constraining both packages. [FastMCP](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-3)

Edit `pyproject.toml`:

```toml
[project]
name = "mcp-elicitation-lab"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastmcp==4.0.0b1",
]

[tool.uv]
constraint-dependencies = [
    "fastmcp-slim==4.0.0b1",
]
```

Then:

```bash
uv sync
uv run fastmcp version
```

The general FastMCP recommendation is to use `uv` for dependency management. [FastMCP](https://gofastmcp.com/getting-started/installation)

---

# 5. Before coding: design the state machine

Do **not** start by asking:

> “Which FastMCP function do I call?”

Start with:

> “What states can this operation occupy?”

For our first tool:

```text
             no answer yet
START ----------------------------+
                                   |
                                   v
                          INPUT REQUIRED
                                   |
                     +-------------+-------------+
                     |                           |
                  accepted                    declined
                     |                           |
                     v                           v
                  EXECUTE                     CANCEL
```

This is a small **state machine**.

That mental model becomes increasingly important with multi-turn elicitation.

---

# 6. The fundamental modern pattern

Conceptually, our tool will look like:

```python
if user_has_not_answered:
    return ask_user()

if user_declined:
    return "Cancelled"

perform_operation()
return "Done"
```

Notice what is missing:

```python
await user_answer
```

There is no blocked server call.

That is the core idea.

---

# 7. Minimal modern FastMCP elicitation

Create:

```text
main.py
```

Start with the server:

```python
from fastmcp import FastMCP, Context
from mcp.types import (
    InputRequiredResult,
    ElicitRequest,
    ElicitRequestFormParams,
)

mcp = FastMCP("Elicitation Lab")
```

Now define a small helper:

```python
def ask_confirmation(message: str) -> InputRequiredResult:
    params = ElicitRequestFormParams(
        message=message,
        requested_schema={
            "type": "object",
            "properties": {
                "approved": {
                    "type": "boolean"
                }
            },
            "required": ["approved"],
        },
    )

    request = ElicitRequest(
        method="elicitation/create",
        params=params,
    )

    return InputRequiredResult(
        result_type="input_required",
        input_requests={
            "confirmation": request
        },
    )
```

Then the tool:

```python
@mcp.tool
async def publish_report(ctx: Context) -> str | InputRequiredResult:
    responses = ctx.input_responses

    if responses is None:
        return ask_confirmation(
            "Publish the quarterly report?"
        )

    answer = responses["confirmation"]

    if answer.action != "accept":
        return "Publication cancelled."

    approved = answer.content["approved"]

    if not approved:
        return "Publication rejected."

    return "Report published."
```

This follows FastMCP's documented modern-protocol pattern: inspect `ctx.input_responses`; if input is absent, return an `InputRequiredResult`; on the next invocation, consume the corresponding response. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 8. Read the code like a protocol engineer

This line:

```python
responses = ctx.input_responses
```

means:

> “Did this invocation arrive carrying answers from an earlier MRTR round?”

First invocation:

```python
ctx.input_responses is None
```

So we return:

```python
InputRequiredResult(...)
```

Think of that as roughly:

```json
{
  "resultType": "input_required",
  "inputRequests": {
    "confirmation": {
      "type": "elicitation",
      "message": "Publish the quarterly report?"
    }
  }
}
```

The MCP client obtains the answer.

Then another request occurs.

Conceptually:

```text
tools/call
    tool: publish_report
    inputResponses:
        confirmation:
            action: accept
            content:
                approved: true
```

The tool starts again from its first line.

Now:

```python
ctx.input_responses
```

contains the answer.

That is MRTR.

The official MCP release describes precisely this sequence: `input_required` → client fulfils the request → original operation is retried with `inputResponses`. [Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/?utm_source=chatgpt.com)

---

# 9. Why the key `"confirmation"` exists

Here:

```python
input_requests={
    "confirmation": request
}
```

`confirmation` is a **correlation key**.

Later:

```python
answer = responses["confirmation"]
```

This matters because one round may request multiple inputs:

```python
input_requests={
    "approval": ...,
    "region": ...,
    "ticket": ...,
}
```

The key correlates:

```text
request ───────────── response

approval       <----> approval
region         <----> region
ticket         <----> ticket
```

Professional term:

> **correlation identifier/key**

---

# 10. Why use JSON Schema?

This:

```python
requested_schema={
    "type": "object",
    "properties": {
        "approved": {
            "type": "boolean"
        }
    },
    "required": ["approved"],
}
```

is not merely documentation.

It is the **data contract between server and client**.

The server says:

```text
I require an object
with an "approved" property
whose value must be boolean.
```

A capable client can turn that into:

```text
┌──────────────────────────────┐
│ Publish quarterly report?    │
│                              │
│ [ Approve ] [ Reject ]       │
└──────────────────────────────┘
```

instead of asking an LLM to interpret arbitrary prose.

That is one major reason elicitation is **structured** rather than just “ask the user a question.”

---

# 11. `accept` does NOT mean "yes"

This distinction causes bugs.

Consider:

```python
answer.action == "accept"
```

It means:

> The user accepted the elicitation interaction and submitted data.

Their submitted data might still be:

```python
approved = False
```

So there are two separate concepts:

```text
Protocol decision
    accept
    decline
    cancel

Business decision
    approved = true
    approved = false
```

Therefore this is correct:

```python
if answer.action != "accept":
    return "Publication cancelled."

if not answer.content["approved"]:
    return "Publication rejected."
```

Do not conflate **protocol outcome** with **domain value**.

---

# 12. The most important coding principle

A modern elicitation tool must tolerate being executed multiple times.

That means this is dangerous:

```python
@mcp.tool
async def deploy(ctx):
    delete_old_servers()

    if ctx.input_responses is None:
        return ask_user()

    create_new_servers()
```

Round 1:

```text
delete_old_servers()
ask user
```

Round 2:

```text
delete_old_servers()    <-- AGAIN
continue
```

You could destroy things twice.

Instead:

```python
@mcp.tool
async def deploy(ctx):
    if ctx.input_responses is None:
        return ask_user()

    # destructive side effect only after approval
    delete_old_servers()
    create_new_servers()
```

This leads to a critical production term:

### Idempotency

An operation is **idempotent** when repeating it does not produce additional unintended effects.

Because MRTR causes re-entry, thinking about:

- idempotency
- side-effect boundaries
- replay safety

is mandatory.

A professional review comment would be:

> “Move the mutation behind the elicitation guard; otherwise the pre-guard side effect is replayed on every MRTR round.”

---

# 13. Mental model to retain

Do **not** picture:

```text
tool
 |
 | await ctx.elicit()
 |
 +------ suspended coroutine ------+
                                   |
                              user answers
                                   |
 +---------------------------------+
 |
 continue
```

For modern MCP picture:

```text
ROUND 1

Client  -------- tools/call -------> Server
Client  <---- input_required ------- Server


ROUND 2

Client
  |
  +-- collect human input
  |
  +------- tools/call ------------> Server
           + inputResponses

Client  <------- final result ------ Server
```

Every horizontal exchange is independent.

That is the architectural shift introduced by MCP `2026-07-28`. [Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/?utm_source=chatgpt.com)

---

# Your first exercise

Before adding the client, modify the tool mentally to support:

```text
"Deploy release v1.7.3 to production?"
```

The elicitation should collect:

```python
{
    "approved": bool,
    "change_ticket": str
}
```

Think in this order:

```text
1. What decision/input does the server need?
2. What schema represents it?
3. What correlation key identifies it?
4. What happens for accept?
5. What happens for decline/cancel?
6. Where is the side-effect boundary?
7. What code might execute again on another MRTR round?
```

That seven-question sequence is the **coding thought process** I want you to internalize.

Next, the natural step is to build the **FastMCP client ourselves**, implement the elicitation handler, and watch the same logical tool call execute across multiple rounds. That is where `response_type`, `ElicitResult`, `inputResponses`, and FastMCP's automatic MRTR loop become concrete.

---

**Post-2026-07-28 spec.**

Specifically, I’ll teach against **MCP `2026-07-28`**, where elicitation is implemented using **Multi Round-Trip Requests (MRTR)** rather than the older stateful server→client callback model. The official MCP release confirms that `elicitation/create`-style server-initiated requests were reworked so the server returns `resultType: "input_required"` and the client retries the original operation with `inputResponses`. [Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/?utm_source=chatgpt.com)

### What that means for the course

```text
Pre-2026-07-28

Client ─── tool call ───> Server
                           │
                           ├── elicitation/create ──> Client
                           │          ↓
                           │     user responds
                           │<────────────────────────
                           │
Client <── final result ───┘
```

versus:

```text
Post-2026-07-28

Client ─── tool call ──────────────> Server
Client <── input_required ───────── Server

        user supplies input

Client ─── same operation ─────────> Server
         + inputResponses
         + requestState (if used)

Client <── final result ──────────── Server
```

This change goes together with MCP's new **stateless protocol core**: the handshake/session model was removed, and MRTR was introduced specifically to support things such as elicitation without holding open bidirectional state. [Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/?utm_source=chatgpt.com)

### One adjustment to my previous lesson

I also want us to distinguish these carefully:

- **Protocol-level MCP 2026-07-28** — the thing we ultimately need to understand.
- **FastMCP's abstraction over that protocol** — convenient Python APIs.
- **Pre-2026-07-28 FastMCP examples** — useful historically, but potentially misleading for new production designs.

I will **not teach the old `await ctx.elicit()` mental model as the fundamental architecture**. We may examine it later specifically as a migration/comparison exercise.

Our next lesson should therefore start even lower-level:

```text
tools/call
      ↓
InputRequiredResult
      ↓
inputRequests
      ↓
client obtains answer
      ↓
inputResponses
      ↓
tools/call retry
```

Then we'll implement that with **Python + uv + FastMCP**, so you understand both the protocol and the framework rather than merely memorizing FastMCP APIs. [Model Context Protocol Blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/?utm_source=chatgpt.com)

---

# Lesson 2 — Build the complete MRTR elicitation loop

We’ll now implement the first real **post-2026-07-28** elicitation flow:

```text
┌──────────┐          tools/call           ┌──────────┐
│  Client  │ ────────────────────────────> │  Server  │
└──────────┘                               └────┬─────┘
                                               │
                                      missing approval
                                               │
┌──────────┐       InputRequiredResult         │
│  Client  │ <─────────────────────────────────┘
└────┬─────┘
     │
     │ elicitation_handler()
     │ asks human
     │
     ▼
 human answers
     │
     │       tools/call + inputResponses
     └───────────────────────────────────────> Server
                                                │
                                                │ sees response
                                                │ performs action
                                                ▼
                                         terminal result
```

Under MCP `2026-07-28`, every round is an independent request/response cycle. The server returns `InputRequiredResult`; the client fulfills the embedded request and retries the original operation with matching `inputResponses`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr?utm_source=chatgpt.com)

---

## 1. Verify the lab

FastMCP 4 is still prerelease as of August 12, 2026; the official docs currently specify `4.0.0b1` for the v4 beta. [FastMCP](https://gofastmcp.com/getting-started/installation?utm_source=chatgpt.com)

Run:

```bash
uv run fastmcp version
```

You want something resembling:

```text
FastMCP version: 4.0.0b1
MCP version:     2.0.0
```

If your previous lab is already configured, don't reinstall anything.

Our project:

```text
mcp-elicitation-lab/
├── pyproject.toml
├── server.py
└── client.py
```

---

# 2. Define the problem before the API

We're building:

```text
deploy_release(version="v1.7.3", environment="production")
```

But production deployment needs:

```text
approved: bool
change_ticket: str
```

The important design decision is:

> These are **not ordinary initial tool parameters** because we're modelling information requested during execution.

So our state machine is:

```text
                    ┌────────────────────┐
                    │ deploy_release()   │
                    └─────────┬──────────┘
                              │
                     inputResponses?
                       /             \
                     no               yes
                     │                 │
                     ▼                 ▼
            request approval       inspect action
                                      │
                         ┌────────────┼────────────┐
                         │            │            │
                      accept       decline       cancel
                         │            │            │
                         ▼            └─────┬──────┘
                 approved=true?            │
                   /        \               ▼
                 yes         no          terminate
                  │           │
                  ▼           ▼
               deploy       reject
```

That's the **guard pattern** FastMCP documents for modern MCP. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 3. Server implementation

Create `server.py`:

```python
from fastmcp import FastMCP, Context
from mcp.types import (
    ElicitRequest,
    ElicitRequestFormParams,
    InputRequiredResult,
)

mcp = FastMCP("Deployment Server")


def request_deployment_approval(
    version: str,
    environment: str,
) -> InputRequiredResult:
    params = ElicitRequestFormParams(
        message=f"Deploy {version} to {environment}?",
        requested_schema={
            "type": "object",
            "properties": {
                "approved": {
                    "type": "boolean",
                    "description": "Whether the deployment is approved",
                },
                "change_ticket": {
                    "type": "string",
                    "description": "Associated change-management ticket",
                },
            },
            "required": [
                "approved",
                "change_ticket",
            ],
        },
    )

    elicitation = ElicitRequest(
        method="elicitation/create",
        params=params,
    )

    return InputRequiredResult(
        result_type="input_required",
        input_requests={
            "deployment_approval": elicitation,
        },
    )


@mcp.tool
async def deploy_release(
    version: str,
    environment: str,
    ctx: Context,
) -> str | InputRequiredResult:

    responses = ctx.input_responses

    # ROUND 1
    if responses is None:
        return request_deployment_approval(
            version=version,
            environment=environment,
        )

    # ROUND 2
    answer = responses["deployment_approval"]

    if answer.action != "accept":
        return f"Deployment stopped: {answer.action}."

    approved = answer.content["approved"]
    change_ticket = answer.content["change_ticket"]

    if not approved:
        return "Deployment rejected by user."

    # Real destructive work would begin AFTER the guard.
    return (
        f"SIMULATED DEPLOYMENT: "
        f"{version} -> {environment} "
        f"under {change_ticket}"
    )
```

This follows FastMCP's documented modern pattern: read `ctx.input_responses`; if absent, return an `InputRequiredResult`; later retrieve the response using the same key used in `input_requests`. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 4. Stop and understand the important line

```python
responses = ctx.input_responses
```

This is effectively asking:

> “Is this the initial invocation, or am I being re-entered as part of an MRTR continuation?”

FastMCP documents:

```text
First invocation:

ctx.input_responses is None
```

Later invocation:

```text
ctx.input_responses = {
    "deployment_approval": ...
}
``` :chatgpt-content-reference{index="4"}


This makes `input_responses` a **request-scoped continuation input**.

Professional vocabulary:

> “The guard branches based on whether the invocation contains continuation input.”

---

# 5. Why this key matters

Server:

```python
input_requests={
    "deployment_approval": elicitation
}
```

Later:

```python
answer = responses["deployment_approval"]
```

Conceptually:

```text
inputRequests
└── deployment_approval
        │
        │ correlation
        ▼
inputResponses
└── deployment_approval
```

The MCP specification defines `InputResponses` as a map whose keys correspond to the keys originally supplied in `InputRequests`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr?utm_source=chatgpt.com)

Call this a:

**correlation key**

or:

**request correlation identifier**

---

# 6. What FastMCP is building for us

This Python:

```python
return InputRequiredResult(
    result_type="input_required",
    input_requests={
        "deployment_approval": elicitation,
    },
)
```

roughly represents this MCP response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "deployment_approval": {
        "method": "elicitation/create",
        "params": {
          "message": "Deploy v1.7.3 to production?",
          "requestedSchema": {
            "type": "object",
            "properties": {
              "approved": {
                "type": "boolean"
              },
              "change_ticket": {
                "type": "string"
              }
            },
            "required": [
              "approved",
              "change_ticket"
            ]
          }
        }
      }
    }
  }
}
```

That `InputRequiredResult` structure and its `inputRequests` / `requestState` fields are defined directly by the current MCP specification. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr?utm_source=chatgpt.com)

Notice something important:

```text
elicitation/create
```

still exists.

What disappeared is the old:

```text
Server ── independent elicitation/create request ──> Client
```

Instead, `elicitation/create` is **embedded inside**:

```text
InputRequiredResult.inputRequests
```

The current elicitation specification explicitly defines this mechanism. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation?utm_source=chatgpt.com)

---

# 7. Now build the client

Create `client.py`:

```python
import asyncio

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult

from server import mcp


async def elicitation_handler(
    message,
    response_type,
    params,
    context,
):
    print()
    print(f"SERVER ASKS: {message}")

    decision = input(
        "Approve? [yes/no/decline/cancel]: "
    ).strip().lower()

    if decision == "decline":
        return ElicitResult(
            action="decline",
        )

    if decision == "cancel":
        return ElicitResult(
            action="cancel",
        )

    approved = decision in {
        "yes",
        "y",
    }

    change_ticket = input(
        "Change ticket: "
    ).strip()

    response = response_type(
        approved=approved,
        change_ticket=change_ticket,
    )

    return ElicitResult(
        action="accept",
        content=response,
    )


async def main():
    async with Client(
        mcp,
        mode="auto",
        elicitation_handler=elicitation_handler,
        input_required_max_rounds=3,
    ) as client:

        result = await client.call_tool(
            "deploy_release",
            {
                "version": "v1.7.3",
                "environment": "production",
            },
        )

        print()
        print("FINAL RESULT:")
        print(result.data)


if __name__ == "__main__":
    asyncio.run(main())
```

FastMCP uses the same `elicitation_handler` abstraction for modern MRTR elicitation. With a `2026-07-28` connection, `Client` automatically fulfills each `InputRequiredResult` and retries the operation until a terminal result appears. [FastMCP](https://gofastmcp.com/clients/elicitation)

---

# 8. Run it

```bash
uv run python client.py
```

Try:

```text
SERVER ASKS: Deploy v1.7.3 to production?

Approve? [yes/no/decline/cancel]: yes
Change ticket: CHG-4821

FINAL RESULT:
SIMULATED DEPLOYMENT: v1.7.3 -> production under CHG-4821
```

Don't focus on the terminal prompts.

Focus on what actually happened.

---

# 9. Trace the execution

This is the important part.

## Invocation #1

Client executes:

```python
await client.call_tool(
    "deploy_release",
    {
        "version": "v1.7.3",
        "environment": "production",
    },
)
```

Server starts:

```python
async def deploy_release(...):
```

Then:

```python
ctx.input_responses
```

is:

```python
None
```

Therefore:

```python
return request_deployment_approval(...)
```

The function is now **finished**.

Not suspended.

Not waiting.

Finished.

FastMCP's modern elicitation documentation explicitly states that nothing stays alive between these rounds. [FastMCP](https://gofastmcp.com/servers/elicitation)

---

# 10. Client receives `input_required`

FastMCP's client sees:

```text
resultType = input_required
```

and discovers:

```text
inputRequests
└── deployment_approval
      └── elicitation/create
```

Because we registered:

```python
elicitation_handler=elicitation_handler
```

FastMCP invokes our handler. The official client documentation states that `response_type` is generated from the form request's JSON Schema so that the handler can construct properly typed response data. [FastMCP](https://gofastmcp.com/clients/elicitation)

That's why this works:

```python
response_type(
    approved=True,
    change_ticket="CHG-4821",
)
```

---

# 11. Very important abstraction

Where did `response_type` come from?

We never wrote:

```python
@dataclass
class DeploymentApproval:
    approved: bool
    change_ticket: str
```

Instead, the server supplied:

```json
{
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "change_ticket": {"type": "string"}
    }
}
```

FastMCP converts the elicitation schema into a Python dataclass type for the client handler. [FastMCP](https://gofastmcp.com/clients/elicitation)

Conceptually:

```text
JSON Schema

        ↓ FastMCP

Python response type

        ↓

response_type(
    approved=True,
    change_ticket="CHG-4821"
)
```

Professional term:

**schema-driven type generation**

---

# 12. The handler returns an `ElicitResult`

We return:

```python
ElicitResult(
    action="accept",
    content=response,
)
```

Conceptually:

```json
{
  "action": "accept",
  "content": {
    "approved": true,
    "change_ticket": "CHG-4821"
  }
}
```

The official MCP MRTR example uses this same bare-result structure inside `inputResponses`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr?utm_source=chatgpt.com)

---

# 13. Then something subtle happens

You did **not** write:

```python
await client.call_tool(...)
await client.call_tool(...)
```

You only wrote:

```python
await client.call_tool(...)
```

once.

Yet the server executes twice.

Why?

FastMCP's `Client` implements the MRTR orchestration loop automatically. It sees `input_required`, fulfills the requests with configured handlers, and reissues the original operation. [FastMCP](https://gofastmcp.com/clients/elicitation)

Conceptually FastMCP is doing:

```python
result = call_tool(...)

while result.result_type == "input_required":
    responses = fulfill(result.input_requests)

    result = call_tool(
        ...,
        input_responses=responses,
        request_state=result.request_state,
    )

return result
```

That's not FastMCP source code; it's the correct conceptual model of the documented behavior.

---

# 14. Invocation #2

The tool starts again:

```python
async def deploy_release(...):
```

Same function.

Same arguments:

```python
version = "v1.7.3"
environment = "production"
```

But now:

```python
ctx.input_responses
```

contains:

```text
deployment_approval
    action = accept
    content
        approved = true
        change_ticket = CHG-4821
```

So this branch is skipped:

```python
if responses is None:
```

and execution continues:

```python
answer = responses["deployment_approval"]
```

Then:

```python
approved = answer.content["approved"]
change_ticket = answer.content["change_ticket"]
```

Finally:

```python
return "SIMULATED DEPLOYMENT..."
```

That's a **terminal result**.

The MRTR loop ends.

---

# 15. `accept`, `decline`, and `cancel`

These are **protocol interaction outcomes**, not your business decision. FastMCP documents all three actions. [FastMCP](https://gofastmcp.com/clients/elicitation)

```text
ElicitResult.action

accept
    User completed the elicitation.

decline
    User chose not to provide the requested information.

cancel
    User cancelled the interaction.
```

Therefore:

```python
action == "accept"
```

doesn't mean:

```python
approved == True
```

This is perfectly valid:

```python
ElicitResult(
    action="accept",
    content=response_type(
        approved=False,
        change_ticket="CHG-4821",
    ),
)
```

Meaning:

```text
Protocol:
    "I completed your form."

Business:
    "No, I don't approve."
```

Professionally:

> **Transport/protocol outcome and domain decision are separate concerns.**

---

# 16. The most important safety property

Notice where our mutation would occur:

```python
if responses is None:
    return request_deployment_approval(...)
```

before:

```python
# perform deployment
```

Correct:

```text
GUARD
  ↓
APPROVAL
  ↓
SIDE EFFECT
```

Dangerous:

```text
SIDE EFFECT
  ↓
GUARD
  ↓
MRTR retry
  ↓
SIDE EFFECT AGAIN
```

Since the tool is re-entered from the top for each round, pre-guard side effects can be replayed. FastMCP explicitly describes each MRTR round as fresh execution. [FastMCP](https://gofastmcp.com/servers/elicitation)

This is where three professional concepts matter:

- **replay safety**
- **idempotency**
- **side-effect boundary**

A strong engineering review comment would be:

> “Move the mutation behind the MRTR guard so replayed invocations remain side-effect free until approval has been established.”

---

# 17. Why `input_required_max_rounds=3`?

We configured:

```python
input_required_max_rounds=3
```

Imagine a broken server:

```python
if responses is None:
    return ask()

return ask()
```

It never reaches a terminal state.

Without a limit:

```text
ask
→ answer
→ ask
→ answer
→ ask
→ ...
```

FastMCP therefore caps the automatic loop. The default is currently **10 rounds**; we deliberately lowered it to `3` for this lab. [FastMCP](https://gofastmcp.com/servers/elicitation)

Professional term:

**bounded retry / bounded interaction loop**

---

# 18. What FastMCP is hiding

Our code looks easy:

```python
result = await client.call_tool(...)
```

But underneath there are at least three layers:

```text
┌─────────────────────────────────────────────┐
│ Application                                │
│ deploy_release()                           │
├─────────────────────────────────────────────┤
│ FastMCP                                    │
│ Client, Context, InputRequiredResult       │
│ MRTR orchestration                         │
├─────────────────────────────────────────────┤
│ MCP 2026-07-28                             │
│ tools/call                                 │
│ InputRequiredResult                        │
│ inputRequests                              │
│ inputResponses                             │
├─────────────────────────────────────────────┤
│ Transport                                  │
│ stdio / HTTP / etc.                        │
└─────────────────────────────────────────────┘
```

Being able to distinguish those layers matters.

If someone asks:

> “Is `ctx.input_responses` part of MCP?”

A precise answer is:

> "`inputResponses` is an MCP protocol concept; `ctx.input_responses` is FastMCP's Python API exposing that request-scoped protocol data."

---

# 19. Vocabulary from this lesson

| Term | Meaning |
|---|---|
| **MRTR** | Multi Round-Trip Request |
| **Guard pattern** | Re-enter operation and check for required continuation data |
| **InputRequiredResult** | Non-terminal result requesting more client input |
| **inputRequests** | Requests client must fulfill |
| **inputResponses** | Results supplied by the client on retry |
| **Correlation key** | Key matching an input request with its response |
| **Terminal result** | Final result that ends the MRTR loop |
| **Continuation input** | Data supplied to continue a previous logical operation |
| **Re-entry** | Tool begins execution again from its entry point |
| **Replay safety** | Safety when an operation or part of it executes again |
| **Idempotency** | Repetition doesn't introduce additional unintended effects |
| **Side-effect boundary** | Point after which persistent mutation is allowed |
| **Schema-driven typing** | Generating programming-language types from a schema |
| **Human-in-the-loop / HITL** | Explicit human participation in an automated workflow |

---

# 20. Coding thought process

Before writing an eliciting MCP tool, reason in this order:

```text
1. What information becomes necessary during execution?

2. Why can't it simply be an initial tool argument?

3. What schema represents the required information?

4. What correlation key identifies the request?

5. What are the valid protocol outcomes?
   accept / decline / cancel

6. What are the business outcomes?
   approved / rejected / etc.

7. Which code executes before the guard?

8. Is any of that code stateful or destructive?

9. What happens when the function starts again?

10. How does the logical operation eventually terminate?
```

That is much more valuable than memorizing:

```python
InputRequiredResult(...)
```

---

# 21. Hands-on exercise

Now modify the lab so deployment approval collects:

```text
approved: bool
change_ticket: str
reason: str
```

Then add this policy:

```text
production
    → approval required

staging
    → no approval required
```

Your architecture should become:

```text
                   environment?
                  /            \
             staging          production
                │                 │
                ▼                 ▼
             deploy         approval present?
                              /          \
                            no            yes
                            │              │
                            ▼              ▼
                         elicit          inspect
                                           │
                                      approved?
                                      /       \
                                    yes        no
                                     │          │
                                     ▼          ▼
                                   deploy      stop
```

The key challenge is **not** adding `reason`.

The key challenge is deciding where the guard belongs so:

```text
staging
```

doesn't require an unnecessary MRTR round, while:

```text
production
```

cannot cross the side-effect boundary without approval.

---

## Next lesson

**Lesson 3: implement multi-round elicitation and `requestState`.**

We'll build:

```text
Round 1: choose environment
Round 2: provide change ticket
Round 3: confirm computed deployment plan
Round 4: execute
```

That introduces the most important stateless-MCP concept after `InputRequiredResult`:

```text
requestState
```

and we'll examine why simply storing:

```python
pending_deployments[user_id] = ...
```

on the server undermines the architecture that MCP `2026-07-28` is designed around. [FastMCP](https://gofastmcp.com/servers/elicitation)