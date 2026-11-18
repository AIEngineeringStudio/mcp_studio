# Lesson 6 — Sampling

Sampling answers:

> **How can an MCP server use an LLM without owning that LLM connection itself?**

The core idea is:

```
MCP server
    │
    │ "Please generate something from these messages"
    ▼
MCP client / host
    │
    ├── chooses model
    ├── applies user policy
    ├── may ask for approval
    └── performs inference
    │
    ▼
generation result
    │
    ▼
MCP server continues
```

MCP calls this **sampling**. The client retains control over model access and model selection, so the server does not need the client's model API key. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

There is one major current-version caveat:

> **Sampling is deprecated in MCP `2026-07-28`.** It still exists for compatibility, but the specification says new implementations should not add it; the suggested replacement is usually a direct LLM-provider integration. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/changelog?utm_source=chatgpt.com)

We should still learn it because it exposes several important MCP concepts: client capabilities, model abstraction, multi-round interactions, tool loops, trust boundaries, and the difference between the `2025-11-25` and `2026-07-28` protocol architectures.

---

## 1. First principle: who owns the model?

Consider a normal MCP server:

```
SERVER
│
├── database credentials
├── business logic
└── MCP tools
```

Now suppose a tool needs reasoning:

```python
summarize_document(...)
```

### Architecture A — server-owned LLM

```
MCP client
    │
    ▼
MCP server
    │
    ├── provider API key
    └── call LLM
          │
          ▼
        model
```

The server decides:

```
provider
model
credentials
billing
retry policy
```

### Architecture B — MCP Sampling

```
MCP client
    │
    │ already owns LLM access
    ▼
MCP server
    │
    │ asks client to sample
    ▼
MCP client
    │
    ▼
client's LLM
```

Here the **client owns inference**. The server describes what it needs. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

Professional phrasing:

> **“Sampling decouples server-side workflow logic from client-side model execution.”**

---

# 2. Sampling is not a Tool call

This distinction matters.

A normal MCP tool:

```
MODEL / HOST
     │
     ▼
 tools/call
     │
     ▼
SERVER
```

Sampling goes conceptually the other way:

```
SERVER
   │
   │ needs inference
   ▼
CLIENT'S MODEL
```

So:

```
Tool
=
client asks server to execute capability


Sampling
=
server asks client to provide model inference
```

This is why sampling is categorized as a **client capability**, not a server primitive. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

---

# 3. The protocol request is `sampling/createMessage`

The core protocol object is:

```
CreateMessageRequest
```

with method:

```
sampling/createMessage
```

A request can contain:

```
messages
systemPrompt
modelPreferences
temperature
maxTokens
stopSequences
tools
toolChoice
```

The latest schema continues to define these fields, although sampling itself is deprecated in `2026-07-28`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema?utm_source=chatgpt.com)

Conceptually:

```
CreateMessageRequest
│
├── conversation
├── generation constraints
├── model preferences
└── optional tools
```

---

# 4. Model **preferences**, not model commands

Suppose your server wants a capable reasoning model.

A bad protocol design would require:

```json
{
  "model": "some-provider/model-x"
}
```

What if the client uses another provider?

What if that model isn't available?

MCP therefore supports:

```json
{
  "modelPreferences": {
    "hints": [
      {
        "name": "sonnet"
      }
    ],
    "costPriority": 0.2,
    "speedPriority": 0.4,
    "intelligencePriority": 0.9
  }
}
```

The three normalized priorities are:

```
costPriority
speedPriority
intelligencePriority
```

and hints are advisory. The **client makes the final model selection**. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

Professional wording:

> “The server expresses model-selection preferences rather than binding the client to a provider-specific model identifier.”

---

# 5. Why this abstraction exists

Imagine:

```
SERVER REQUIREMENT

high reasoning quality
moderate latency tolerance
low concern about cost
```

That requirement survives provider changes.

```
Anthropic
OpenAI
Gemini
Local model
Future provider
```

So instead of:

```
implementation identity
```

MCP attempts to communicate:

```
capability requirements
```

This is a classic abstraction principle:

> **Express intent rather than implementation.**

---

# 6. Latest MCP changed the wire architecture

This is the major difference from the previous Roots lesson.

In `2025-11-25`, the server could literally send:

```
SERVER ── sampling/createMessage ──> CLIENT
```

during another request.

In `2026-07-28`, servers **MUST NOT initiate JSON-RPC requests**. Sampling, roots, and elicitation use **Multi Round-Trip Requests (MRTR)** instead. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr?utm_source=chatgpt.com)

The modern pattern is:

```
CLIENT                         SERVER

tools/call
──────────────────────────────>

             "I need an LLM result"
<──────────────────────────────
InputRequiredResult


client performs sampling


tools/call AGAIN
+ inputResponses
+ requestState
──────────────────────────────>

final result
<──────────────────────────────
```

This is fundamentally different.

---

# 7. First principles: why MRTR?

The old architecture needed an open session:

```
request still running
       │
       ├── server calls client
       │
       ├── waits
       │
       └── resumes
```

That makes horizontal scaling harder because execution state lives implicitly inside a live connection.

The modern protocol instead makes each round an independent client request:

```
round 1
complete HTTP request/response

round 2
complete HTTP request/response
```

State required between rounds can be encoded in `requestState`. The specification explicitly says the retry can be processed independently without relying on the original server process or connection. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

Professional terminology:

> **“MRTR externalizes continuation state instead of relying on a session back-channel.”**

---

# 8. Protocol-level modern sampling

Suppose we have:

```
Tool:
summarize_document(text)
```

The client initially calls:

```json
{
  "jsonrpc": "2.0",
  "id": 100,
  "method": "tools/call",
  "params": {
    "name": "summarize_document",
    "arguments": {
      "text": "Very long document..."
    }
  }
}
```

I am omitting the required `2026-07-28` `_meta` fields here only to make the sampling flow easier to read; modern MCP requests carry protocol/client metadata per request. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

The server determines:

```
I need the client's LLM.
```

It does **not** send another JSON-RPC request.

It returns:

```json
{
  "jsonrpc": "2.0",
  "id": 100,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "summary": {
        "method": "sampling/createMessage",
        "params": {
          "messages": [
            {
              "role": "user",
              "content": {
                "type": "text",
                "text": "Summarize this document:\n\nVery long document..."
              }
            }
          ],
          "systemPrompt": "Produce a concise factual summary.",
          "maxTokens": 300
        }
      }
    },
    "requestState": "opaque-server-state"
  }
}
```

`inputRequests` is a map keyed by server-assigned identifiers, and a `CreateMessageRequest` is one of the request types it can contain. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

---

# 9. The client performs inference

The client sees:

```
inputRequests["summary"]
```

and notices:

```
method = sampling/createMessage
```

It can then:

```
1. inspect the request
2. apply policy / approval
3. choose a model
4. invoke the model
5. produce CreateMessageResult
```

MCP recommends user visibility and control for sampling, including the ability to inspect requests and generated responses. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

The result may conceptually be:

```json
{
  "role": "assistant",
  "content": {
    "type": "text",
    "text": "The document describes..."
  },
  "model": "selected-model",
  "stopReason": "endTurn"
}
```

---

# 10. Then the client retries the original request

This is the key MRTR idea.

The client does **not** call:

```
sampling/result
```

There is no such method.

Instead it calls:

```
tools/call
```

again.

```json
{
  "jsonrpc": "2.0",
  "id": 101,
  "method": "tools/call",
  "params": {
    "name": "summarize_document",
    "arguments": {
      "text": "Very long document..."
    },
    "inputResponses": {
      "summary": {
        "role": "assistant",
        "content": {
          "type": "text",
          "text": "The document describes..."
        },
        "model": "selected-model",
        "stopReason": "endTurn"
      }
    },
    "requestState": "opaque-server-state"
  }
}
```

Modern `CallToolRequestParams` explicitly supports `inputResponses` and `requestState`; the retry must use a new JSON-RPC ID because it is a separate request. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema?utm_source=chatgpt.com)

---

# 11. Server resumes logically, not physically

The server sees:

```
inputResponses["summary"]
```

and now has the completion.

It can finish:

```json
{
  "jsonrpc": "2.0",
  "id": 101,
  "result": {
    "resultType": "complete",
    "content": [
      {
        "type": "text",
        "text": "The document describes..."
      }
    ],
    "isError": false
  }
}
```

Conceptually:

```
ROUND 1

tool starts
   │
   └── requires LLM
          │
          ▼
InputRequiredResult


ROUND 2

tool resumes logically
   │
   ├── reads supplied completion
   │
   ▼
final result
```

The important word is **logically**.

The same Python coroutine does not need to remain suspended between rounds in modern MCP. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

---

# 12. `requestState` is continuation state

Suppose round one had already computed:

```
document_id
selected strategy
authorization context
processing stage
```

Modern MCP gives the server:

```
requestState
```

to carry continuation information through the client and back on the retry. The client must treat it as opaque. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

Think:

```
server state
     │
     ▼
serialized continuation
     │
     ▼
requestState
     │
     ▼
client echoes unchanged
     │
     ▼
server reconstructs state
```

Professional terminology:

- **continuation state**
- **opaque state token**
- **stateless continuation**
- **round-trip correlation**

---

# 13. Security warning: requestState crosses a trust boundary

Do not do:

```python
request_state = json.dumps({
    "user_is_admin": True
})
```

and blindly trust it on return.

The state travels through the client.

MCP therefore requires servers to treat `requestState` as attacker-controlled. If it affects authorization, business logic, or resource access, its integrity must be protected—for example with HMAC or AEAD. The specification also recommends binding it to the authenticated principal, expiry, and originating request to reduce replay risk. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

Professional phrase:

> **“Opaque does not mean trusted; request state crossing the client must be integrity protected.”**

---

# 14. Compare old vs modern Sampling

This is worth memorizing.

### MCP `2025-11-25`

```
tool coroutine starts
      │
      ▼
server sends
sampling/createMessage
      │
      ▼
client responds
      │
      ▼
same server operation resumes
```

The protocol directly supported the nested request. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

### MCP `2026-07-28`

```
tools/call
      │
      ▼
InputRequiredResult
      │
      ▼
client performs sampling
      │
      ▼
NEW tools/call
+ inputResponses
      │
      ▼
server finishes
```

Direct server-initiated requests were removed in favor of MRTR. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr?utm_source=chatgpt.com)

---

# 15. FastMCP 3.x abstraction — the old protocol

FastMCP 3.x exposes the older model beautifully:

```python
from fastmcp import Context, FastMCP

mcp = FastMCP("DocumentAssistant")


@mcp.tool
async def summarize(
    text: str,
    ctx: Context,
) -> str:
    result = await ctx.sample(
        f"Summarize this document:\n\n{text}"
    )

    return result.text or ""
```

`ctx.sample()` hides the `sampling/createMessage` RPC and returns a higher-level sampling result. FastMCP's older sampling API can also manage multi-turn/tool-enabled sampling loops. [FastMCP](https://gofastmcp.com/v2/servers/sampling?utm_source=chatgpt.com)

This looks like:

```python
await ctx.sample(...)
```

but under `2025-11-25` it means approximately:

```
construct CreateMessageRequest
        │
        ▼
sampling/createMessage
        │
        ▼
client sampling handler
        │
        ▼
CreateMessageResult
        │
        ▼
SamplingResult
```

---

# 16. Again: Python syntax hides RPC cost

This:

```python
result = await ctx.sample(...)
```

looks similar to:

```python
result = await local_function(...)
```

but operationally it can mean:

```
serialization
network / process transport
user approval
provider inference
token generation
response transport
deserialization
```

So a loop like:

```python
for paragraph in paragraphs:
    await ctx.sample(paragraph)
```

may create a large number of separate LLM calls and protocol round trips.

Professional phrase:

> **“Sampling is a remote inference boundary disguised behind an async method.”**

---

# 17. FastMCP client abstraction

The other half of sampling lives in the client.

FastMCP lets the client register a:

```
sampling_handler
```

For example:

```python
from fastmcp import Client
from fastmcp.client.sampling import (
    RequestContext,
    SamplingMessage,
    SamplingParams,
)


async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    context: RequestContext,
) -> str:
    # Apply policy.
    # Select your model.
    # Call your provider.
    return "Generated response"


client = Client(
    "server.py",
    sampling_handler=sampling_handler,
)
```

The handler receives the requested conversation and sampling parameters. The client remains free to honor, modify, map, or reject model preferences because it owns model execution. [FastMCP](https://gofastmcp.com/clients/sampling)

---

# 18. Peel the client abstraction

This:

```python
Client(
    server,
    sampling_handler=my_handler,
)
```

roughly means:

```
FastMCP Client
│
├── advertise sampling support
│
├── receive sampling request
│
├── convert protocol messages
│
├── invoke my_handler(...)
│
├── normalize handler result
│
└── provide CreateMessageResult
```

FastMCP's current client abstraction supports both the older pushed sampling route and the newer MRTR route through the same handler registration. [FastMCP](https://gofastmcp.com/clients/sampling)

That is an example of a framework hiding **protocol-era negotiation**.

---

# 19. FastMCP 4 changed the server abstraction

FastMCP 4 removes:

```python
ctx.sample()
ctx.sample_step()
```

because those methods implied a live server→client back-channel that the modern MCP protocol no longer has. FastMCP's current guidance is either:

```
A. call an LLM directly from your server

or

B. return an InputRequiredResult asking the caller to sample
``` :chatgpt-content-reference{index="20"}


So the abstraction changed because the underlying protocol changed.

This is exactly why learning protocol-first matters.

---

# 20. FastMCP 4's MRTR shape

At the FastMCP 4 beta layer, asking the caller's model looks conceptually like:

```python
from fastmcp import Context, FastMCP
from mcp.types import (
    CreateMessageRequest,
    CreateMessageRequestParams,
    CreateMessageResult,
    InputRequiredResult,
    SamplingMessage,
    TextContent,
)

mcp = FastMCP("Research")


@mcp.tool
async def ask_model(
    question: str,
    ctx: Context,
) -> str | InputRequiredResult:

    if ctx.input_responses is None:
        return InputRequiredResult(
            result_type="input_required",
            input_requests={
                "answer": CreateMessageRequest(
                    method="sampling/createMessage",
                    params=CreateMessageRequestParams(
                        messages=[
                            SamplingMessage(
                                role="user",
                                content=TextContent(
                                    type="text",
                                    text=question,
                                ),
                            )
                        ],
                        max_tokens=200,
                    ),
                )
            },
        )

    answer = ctx.input_responses["answer"]

    if isinstance(answer, CreateMessageResult):
        ...
```

FastMCP documents this return-and-resume pattern for modern connections. [FastMCP](https://gofastmcp.com/servers/sampling)

Notice how different it is from:

```python
await ctx.sample(...)
```

---

# 21. Imperative vs continuation-style API

FastMCP 3:

```python
response = await ctx.sample(...)
return response.text
```

This is an **imperative API**.

The function pauses and resumes.

FastMCP 4 / modern MCP:

```python
if no_answer:
    return InputRequiredResult(...)

answer = ctx.input_responses["answer"]
```

This is a **continuation-style / multi-round API**.

The function may execute from the beginning again on the next request. [FastMCP](https://gofastmcp.com/servers/sampling)

Professional explanation:

> “Modern MCP replaces a suspended server coroutine with explicit continuation state and request replay.”

---

# 22. Sampling messages

Sampling messages use:

```
role:
    user
    assistant
```

and support text, image, and audio content. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

Example:

```json
{
  "role": "user",
  "content": {
    "type": "text",
    "text": "Classify this incident."
  }
}
```

Unlike Prompt messages, the sampling conversation is specifically the conversation sent to an LLM for generation.

---

# 23. `systemPrompt`

Sampling has an explicit:

```
systemPrompt
```

field.

This is different from the Prompt primitive we learned previously, where `PromptMessage.role` only had `user` and `assistant`.

Example:

```json
{
  "systemPrompt": "Return only a concise operational summary."
}
```

The sampling protocol therefore separately models:

```
system instruction
+
conversation messages
``` :chatgpt-content-reference{index="24"}


---

# 24. Stop reasons

A sampling result can tell you why generation stopped.

Typical values include:

```
endTurn
stopSequence
maxTokens
toolUse
``` :chatgpt-content-reference{index="25"}


This matters.

Bad:

```python
if response.text:
    done()
```

Better:

```
stopReason == endTurn
    → likely final response

stopReason == maxTokens
    → response may be truncated

stopReason == toolUse
    → model is asking for tool execution
```

Stop reason is part of control flow, not mere debugging metadata.

---

# 25. Sampling can itself use tools

This is where things become agentic.

A sampling request can include:

```json
{
  "tools": [
    {
      "name": "get_inventory",
      "description": "Get stock for one SKU",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sku": {
            "type": "string"
          }
        },
        "required": ["sku"]
      }
    }
  ],
  "toolChoice": {
    "mode": "auto"
  }
}
```

Tool-enabled sampling requires the client to declare `sampling.tools` support. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

Now:

```
SERVER
  │
  │ sampling request + tools
  ▼
CLIENT'S LLM
  │
  ▼
tool_use
  │
  ▼
SERVER executes sampling tool
  │
  ▼
tool_result
  │
  ▼
another sampling round
```

---

# 26. This is an agent loop

Suppose the model receives:

```
"Compare current inventory in Phoenix and Dallas."
```

It responds:

```
tool_use:
get_inventory(PHX)

tool_use:
get_inventory(DFW)
```

The server executes both.

Then the server supplies:

```
PHX → 27
DFW → 11
```

back to another model sampling round.

The model returns:

```
"Phoenix has 16 more units than Dallas."
```

The stable `2025-11-25` sampling specification explicitly defines this multi-turn tool loop and supports multiple parallel tool-use blocks. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

---

# 27. Important ownership rule

A sampling handler does **not necessarily execute the tools**.

The protocol flow is:

```
client's LLM
     │
     ▼
requests tool use
     │
     ▼
sampling result sent to server
     │
     ▼
SERVER executes supplied sampling tool
```

FastMCP's client sampling documentation explicitly says the handler passes tool definitions to the model and returns tool calls; the **server** is responsible for executing them and issuing any follow-up sampling request. [FastMCP](https://gofastmcp.com/clients/sampling)

Professional phrase:

> **“The client owns inference; the server owns sampling-loop tool execution.”**

---

# 28. Tool-choice modes

MCP defines:

```
auto
required
none
```

for sampling tool choice.

```
auto
→ model decides

required
→ model must use at least one tool

none
→ model may not call tools
``` :chatgpt-content-reference{index="29"}


Use this as **model steering**, not security enforcement.

Your server still has to decide which tool implementations actually exist and what they are permitted to do.

---

# 29. Tool-use/result pairing

Suppose the model returns:

```
tool_use id=call_1
tool_use id=call_2
```

The next user-role tool-result message must provide matching results for both before the conversation continues.

```
call_1 → ToolResult
call_2 → ToolResult
```

MCP `2025-11-25` explicitly requires tool-use/result balance and forbids mixing tool-result blocks with unrelated text/image/audio blocks in the same tool-result message. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

This solves provider interoperability problems.

---

# 30. Never create an unbounded sampling loop

Imagine:

```
LLM requests tool
→ server executes tool
→ LLM requests another tool
→ server executes
→ ...
```

Without limits:

```
latency
cost
resource consumption
recursive failure
```

can grow indefinitely.

The MCP sampling specification recommends iteration limits for tool loops. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

A sensible application-level design includes:

```python
MAX_ROUNDS = 5
```

and perhaps:

```
last round:
toolChoice = none
```

to request a final answer.

---

# 31. Sampling is not deterministic business logic

Bad design:

```
"Ask the LLM whether the user has permission."
```

Authorization belongs in deterministic application logic.

Bad:

```
"Ask the LLM whether we should charge the credit card."
```

Critical business invariants should not depend on unconstrained model output.

Better use cases:

```
summarization
classification with validation
drafting
reasoning assistance
natural-language transformation
ranking suggestions
extracting candidates for later validation
```

Sampling should augment deterministic logic, not replace security or correctness boundaries.

---

# 32. Trust boundary

Sampling means the server can propose content for:

```
client's model
```

That content may include:

```
untrusted database values
user content
external documents
tool outputs
```

The client may also return generated content that the server must treat as untrusted model output.

The protocol therefore recommends user approval controls, message validation, rate limiting, and appropriate handling of sensitive data. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

Think:

```
SERVER DATA
    │
    ▼
sampling request
    │
    ▼
MODEL
    │
    ▼
generated data
    │
    ▼
SERVER
```

There are trust boundaries in **both directions**.

---

# 33. Sampling failure is not necessarily Tool failure

Suppose:

```
summarize_document tool
        │
        ▼
sampling request
        │
        ▼
user rejects sampling
```

The sampling interaction may fail, but your outer tool must decide what that means:

```
fail tool
fallback
return partial result
use deterministic method
ask user differently
```

For legacy direct sampling, the spec recommends an error when the user rejects the sampling request. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

The important design principle:

> **Nested RPC failure and outer-operation failure are separate decisions.**

---

# 34. When should a server own the LLM instead?

This is now especially important because modern MCP deprecates Sampling.

Choose a **direct provider API** when:

```
you require a specific model
you own billing
you need predictable provider behavior
you need retries/caching centrally
you don't need the caller's model identity
you need the feature to work across clients
```

FastMCP's current documentation explicitly recommends direct model calls for the normal case and describes sampling as worthwhile mainly when borrowing the caller's model is itself the desired behavior. [FastMCP](https://gofastmcp.com/servers/sampling)

Choose sampling only when:

```
using the caller's model is semantically important
```

That is a much stronger design test than:

```
"Sampling looks convenient."
```

---

# 35. Complete protocol → FastMCP mapping

| Protocol concept | FastMCP 3.x | FastMCP 4 beta |
|---|---|---|
| `sampling/createMessage` | `ctx.sample()` | `CreateMessageRequest` inside `InputRequiredResult` |
| client capability | `sampling_handler=` | same client handler |
| sampling messages | Python sampling objects | MCP type objects |
| model preferences | `ctx.sample(...)` options | `CreateMessageRequestParams` |
| client result | `SamplingResult` abstraction | `ctx.input_responses[...]` |
| nested request | hidden by coroutine | replaced by MRTR |
| continuation | suspended call | explicit retry |
| tool loop | `ctx.sample()` / `sample_step()` | application-managed rounds |
| client model provider | sampling handler | sampling handler |

FastMCP's current client intentionally handles both protocol-era routes through the same `sampling_handler`. [FastMCP](https://gofastmcp.com/clients/sampling)

---

# 36. Vocabulary checkpoint

| Term | Meaning |
|---|---|
| **Sampling** | Requesting LLM inference through the MCP client |
| **CreateMessageRequest** | Protocol representation of a sampling request |
| **CreateMessageResult** | Client's generated sampling response |
| **Model preference** | Advisory model-selection requirement |
| **Model hint** | Suggested model/model-family identifier |
| **Sampling handler** | Client callback that performs model inference |
| **Nested inference** | LLM generation occurring during another MCP operation |
| **Agent loop** | model → tool → result → model cycle |
| **Tool choice** | Policy controlling whether model tools may/must be used |
| **Stop reason** | Why a generation round terminated |
| **MRTR** | Multi Round-Trip Requests |
| **InputRequiredResult** | Interim result saying more client input is required |
| **InputRequests** | Server-described requests client must fulfill |
| **InputResponses** | Client-supplied answers on retry |
| **Continuation state** | Information needed to resume logical processing |
| **requestState** | Opaque continuation token passed through the client |
| **Back-channel** | Legacy live server→client request path |
| **Caller-owned inference** | Client controls provider/model/credentials |
| **Server-owned inference** | Server invokes an LLM provider directly |

A strong professional explanation is:

> **“Sampling lets an MCP server borrow inference from the caller while leaving model selection and permissions client-controlled. In `2025-11-25` this was a nested server-initiated `sampling/createMessage` RPC, which FastMCP 3 abstracts as `ctx.sample()`. In `2026-07-28`, server-initiated requests were replaced by MRTR, so the server returns an `InputRequiredResult` containing a `CreateMessageRequest`, and the client retries the original operation with a `CreateMessageResult` in `inputResponses`.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)

---

# 37. Hands-on exercise

For learning, use **FastMCP 3.4.7** for the first part so you can observe the legacy sampling abstraction directly. [GitHub](https://github.com/PrefectHQ/fastmcp/releases?utm_source=chatgpt.com)

Build:

```python
@mcp.tool
async def summarize(
    text: str,
    ctx: Context,
) -> str:
    result = await ctx.sample(
        f"Summarize:\n{text}"
    )
    return result.text or ""
```

Then build a client with a custom:

```python
sampling_handler
```

Do **not** call a real LLM initially.

Return:

```
"FAKE MODEL RESPONSE"
```

That is more useful for learning because you can isolate MCP from provider behavior.

Then test:

1. Call the tool with no sampling handler.
2. Register a sampling handler.
3. Log the incoming `messages`.
4. Inspect `system_prompt`, `max_tokens`, and model preferences.
5. Make the handler reject the request.
6. Add a real provider only after the protocol flow is clear.
7. Add two sample calls and observe that they are two separate inference round trips.
8. Add sampling tools and deliberately trigger `stopReason="toolUse"`.
9. Enforce a maximum iteration count.
10. Finally recreate the same workflow using the modern `InputRequiredResult → inputResponses` model.

The key test is whether you can explain why these are different:

```
ctx.sample(...)
        ≠
LLM provider API call
        ≠
sampling/createMessage
        ≠
InputRequiredResult
```

They exist at different abstraction layers.

---

## Next lesson — Elicitation

Sampling means:

```
SERVER
asks CLIENT
for LLM inference
```

**Elicitation** means:

```
SERVER
asks CLIENT
for USER input
```

We’ll build:

```
elicitation/create
form schemas
accept / decline / cancel
sensitive-input boundaries
progressive disclosure
human-in-the-loop workflows
MRTR continuation
FastMCP ctx.elicit()
FastMCP 4's modern elicitation abstraction
```

Elicitation is the natural next lesson because it uses the same multi-round architecture as Sampling, but the missing input comes from a **human instead of a model**.