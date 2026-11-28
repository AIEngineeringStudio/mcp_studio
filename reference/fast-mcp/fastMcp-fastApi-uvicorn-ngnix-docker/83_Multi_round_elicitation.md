# Lesson 3 — Multi-round elicitation and `requestState`

We’ll make one design decision:

> **How does a stateless MCP server remember information learned in an earlier elicitation round?**

This is where `requestState` becomes necessary.

## 1. Concrete requirement

Suppose our deployment flow needs two human interactions:

```
deploy_release(version="v1.7.3")

Round 1
Ask: Which environment?
User: production

Round 2
Server computes:
- 6 instances affected
- expected downtime: 90 seconds

Ask:
Approve this deployment?
User: yes

Round 3
Perform deployment
```

The logical workflow needs to remember:

```
environment = production
```

between round 1 and round 2.

But MCP `2026-07-28` deliberately does **not** require the same server process to handle both requests. Each MRTR round is an independent request. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

---

# 2. The simple baseline breaks

You might initially imagine:

```python
if environment_response:
    environment = environment_response["environment"]

if approval_response:
    deploy(environment)
```

There is a problem.

`inputResponses` is **the response for the current round**, not a permanent history of all previous answers.

Conceptually:

```
ROUND 1 REQUEST
inputResponses = none


ROUND 2 REQUEST
inputResponses =
    environment:
        production


ROUND 3 REQUEST
inputResponses =
    approval:
        true
```

Round 3 does **not** necessarily contain:

```
environment = production
```

FastMCP explicitly describes `ctx.request_state` as the mechanism for carrying small state from one round into the next. [FastMCP](https://gofastmcp.com/docs/servers/elicitation)

So this model is wrong:

```
inputResponses = conversation history
```

Use this model:

```
inputResponses = answers produced by the immediately preceding round
```

---

# 3. Three ways to retain the environment

### A. Recompute it

Maybe the original tool arguments contain enough information to derive the environment again.

```
original arguments
      |
      v
recompute environment
```

This is simplest when possible.

### B. Store it server-side

For example:

```
pending_deployments[request_id] = {
    environment: "production"
}
```

This works, but now the server owns workflow state.

That creates operational requirements:

```
Replica A
   |
   | stores state
   v
 Redis / DB
   ^
   |
Replica B
```

You need persistence, cleanup, concurrency handling, TTLs, etc.

### C. Carry it through `requestState`

```
Server
  |
  | produces state
  v
requestState
  |
  | echoed unchanged
  v
Client
  |
  | next call
  v
Server
```

For small MRTR workflow state, this is normally the intended design.

The MCP specification explicitly says servers can encode needed context in `requestState`, allowing a retry to be handled without depending on state from the previous server instance. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

---

# 4. What `requestState` actually is

At the protocol level:

```
requestState = opaque string
```

The server creates it.

The client must:

```
receive it
   ↓
not inspect it
   ↓
not modify it
   ↓
send exactly the same value back
```

The specification is strict about this: the client must treat `requestState` as opaque and echo it unchanged on the retry. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

That gives us:

```
ROUND 1

Client
   |
   | tools/call
   v
Server
   |
   | asks environment
   v
input_required


ROUND 2

Client
   |
   | inputResponses:
   |   environment=production
   v
Server
   |
   | learns environment
   |
   | computes deployment plan
   |
   | requestState:
   |   {environment: production, ...}
   |
   | asks approval
   v
input_required


ROUND 3

Client
   |
   | inputResponses:
   |   approval=true
   |
   | requestState:
   |   <opaque token>
   v
Server
   |
   | recovers environment
   | validates approval
   v
deploy
```

---

# 5. The important ownership distinction

This is a useful professional distinction.

| Data | Owner |
|---|---|
| Tool arguments | Client supplies them |
| `inputResponses` | Client supplies answers |
| `requestState` contents | Server owns their meaning |
| `requestState` transport | Client carries it |
| Persistent deployment record | Server/application owns it |

So:

> `requestState` is **server-owned state carried through an untrusted client**.

That phrasing is useful because it immediately exposes the security problem.

---

# 6. Why the client is untrusted

Imagine the server sent state representing:

```
environment = production
approval_stage = awaiting_confirmation
deployment_id = 8271
```

A malicious client might try changing it to:

```
environment = staging
approval_stage = approved
deployment_id = 8271
```

If the server simply trusts decoded JSON, you have created an authorization bypass.

Therefore MCP says `requestState` arriving from a client must be treated as **attacker-controlled input**. If it affects authorization, resource access, or business logic, its integrity must be protected—for example using HMAC or AEAD—and invalid state must be rejected. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

Professional term:

> **Integrity protection**

Different from encryption.

Encryption asks:

```
Can the client read this?
```

Integrity protection asks:

```
Can the client change this without detection?
```

For workflow correctness, integrity is mandatory when tampering matters.

---

# 7. FastMCP changes the implementation detail

At raw MCP level you would need to think about sealing and verification yourself.

FastMCP 4 provides a higher-level abstraction.

Your tool sees:

```
ctx.request_state
```

as plaintext application state.

When you return:

```
InputRequiredResult
    request_state = ...
```

FastMCP seals the state before putting it on the wire, then verifies and unseals it when it returns. Its documentation says tampered, expired, or incorrectly signed state is rejected before the tool receives it. [FastMCP](https://gofastmcp.com/docs/servers/elicitation)

So conceptually:

```
Your tool
    |
    | "environment=production"
    v
FastMCP
    |
    | seal
    v
opaque token
    |
    | CLIENT
    |
    v
opaque token
    |
    | verify + unseal
    v
FastMCP
    |
    v
Your tool
"environment=production"
```

This distinction matters:

```
MCP specification
    defines requestState semantics

FastMCP
    implements secure state handling
```

---

# 8. Our state machine

Do not write the code yet.

First define explicit phases:

```
             first invocation
                    |
                    v
          +-------------------+
          | NEED ENVIRONMENT  |
          +---------+---------+
                    |
               environment
                    |
                    v
          compute deployment
               impact
                    |
                    v
          +-------------------+
          | NEED APPROVAL     |
          +---------+---------+
                    |
                 approved
                 /      \
               yes       no
                |         |
                v         v
             DEPLOY     STOP
```

The state needed after round 2 could conceptually be:

```
phase = awaiting_approval
environment = production
version = v1.7.3
affected_instances = 6
```

This is a **workflow continuation state**.

Professional terminology:

> “`requestState` carries the continuation state needed to resume the workflow on a fresh invocation.”

---

# 9. Why store `phase` explicitly?

You could infer the phase from available responses:

```
if "environment" present:
    must be round 2

if "approval" present:
    must be round 3
```

That works for trivial workflows.

It gets brittle quickly.

A cleaner model is:

```
requestState
    phase = awaiting_approval
```

Then your handler conceptually does:

```
state absent
    → ask environment

state.phase == awaiting_approval
    → read approval

state.phase == ...
    → handle next phase
```

This is called an:

> **explicit state machine**

It is preferable to inferring workflow state from incidental data.

---

# 10. Information flow, exactly

Suppose the user starts with:

```
deploy_release(version="v1.7.3")
```

### Round 1

Request:

```
arguments:
    version = v1.7.3

inputResponses:
    none

requestState:
    none
```

Server returns:

```
resultType:
    input_required

inputRequests:
    environment:
        "Which environment?"
```

No persistent server state is required.

### Round 2

Client retries:

```
arguments:
    version = v1.7.3

inputResponses:
    environment:
        action = accept
        environment = production
```

Server computes:

```
affected_instances = 6
downtime = 90 seconds
```

It now returns:

```
inputRequests:
    approval:
        "Deploy 6 production instances
         with ~90 seconds downtime?"

requestState:
    sealed {
        phase: awaiting_approval
        environment: production
        affected_instances: 6
    }
```

### Round 3

Client retries:

```
arguments:
    version = v1.7.3

inputResponses:
    approval:
        action = accept
        approved = true

requestState:
    <exact opaque token from round 2>
```

FastMCP verifies and exposes:

```
phase = awaiting_approval
environment = production
affected_instances = 6
```

Now the tool has everything required:

```
original argument
    version

previous-round state
    environment
    affected_instances

current response
    approval
```

Only now do we cross the:

> **side-effect boundary**

and perform the deployment.

---

# 11. One realistic failure

Assume:

```
Round 2 handled by Replica A
Round 3 handled by Replica B
```

FastMCP's default request-state protection uses a per-process key.

Therefore:

```
Replica A
   |
   | seals state with Key A
   v
Client
   |
   v
Replica B
   |
   | tries Key B
   X
verification fails
```

FastMCP's documentation explicitly warns about this for horizontally scaled deployments. Replicas must share request-state security keys if consecutive rounds can reach different processes. [FastMCP](https://gofastmcp.com/docs/servers/elicitation)

Architecture:

```
                Load Balancer
                /           \
               /             \
              v               v
        +-----------+   +-----------+
        | Replica A |   | Replica B |
        +-----------+   +-----------+
              \             /
               \           /
                v         v

              same shared
          request-state key
```

This is a good production discussion point:

> “Because MRTR retries may land on different replicas, request-state verification keys must be shared across the deployment.”

---

# 12. What `requestState` should NOT become

Don't turn it into a database.

Bad conceptual state:

```
requestState =
    entire customer record
    500 search results
    full deployment logs
    API credentials
    huge model response
```

Remember:

```
Server → client → server
```

on every round.

FastMCP recommends keeping it small because it travels through the client on each leg. [FastMCP](https://gofastmcp.com/docs/servers/elicitation)

Better:

```
requestState =
    phase
    selected environment
    small computed identifiers
    small values needed for continuation
```

Large durable state belongs elsewhere.

---

# 13. The design rule

For each piece of information ask:

```
Can I derive it again cheaply?
        |
      yes
        |
        v
    recompute


No
 |
 v
Is it small and only needed
for this MRTR workflow?
 |
yes
 |
 v
requestState


No
 |
 v
durable application storage
```

That is a useful decision framework.

---

# 14. Professional vocabulary from this lesson

**Continuation state**  
Information needed to resume a multi-round operation.

**Opaque token**  
A value the carrier transports without understanding.

**Explicit state machine**  
Workflow behavior represented by named phases rather than inferred indirectly.

**Stateless execution**  
Each request can be processed without relying on memory from a previous invocation.

**Integrity protection**  
Cryptographic protection against undetected modification.

**Replay**  
Reusing a previously valid request or state token.

**TTL**  
Time-to-live limiting how long continuation state remains valid.

**Horizontal scaling**  
Running multiple interchangeable server replicas.

**Shared verification key**  
A common cryptographic key allowing different replicas to validate continuation state.

**Side-effect boundary**  
The point after which an operation mutates durable/external state.

---

## The key idea

Do not think:

```
requestState = session
```

Think:

```
requestState =
small, server-owned continuation state
carried through the client
between independent MRTR requests
```

The MCP specification also recommends binding integrity-protected state to things such as the authenticated principal, an expiry, and the originating operation to limit cross-user and replay misuse. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

The next decision is the implementation one: **how to model this deployment workflow cleanly in FastMCP using explicit phases, `ctx.request_state`, and multiple `InputRequiredResult` rounds without creating replay bugs.**