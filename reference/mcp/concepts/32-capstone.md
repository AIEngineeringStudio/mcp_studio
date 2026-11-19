# A ticket service grown one requirement at a time

**Outcome:** Connect the individual concepts into a staged implementation with explicit evidence.

**Prerequisites:** [01: Why MCP exists](01-why-mcp.md), [05: Tools and their contracts](05-tool-contracts.md), [09: Resources, URIs, and templates](09-resources.md), [10: Reusable MCP prompts](10-prompts.md), [14: Continuation state and safe reentry](14-continuation-state.md), [16: Service layers and persistence](16-service-persistence.md), [21: Authorization, scopes, and tenant isolation](21-authorization.md), [25: Timeouts, cancellation, retries, and idempotency](25-reliability.md), [27: Testing and debugging MCP by layer](27-testing.md), [28: Logs, metrics, and traces](28-observability.md).

## The user journey

A support assistant looks up a ticket, reads related context, asks the user
for missing information when necessary, and performs only authorized changes.
The ticket database is the source of truth. The host coordinates interaction.

The supplied labs implement the initial synthetic read-only slice. The
remaining stages below are a worked evolution plan, not a claim that a
production service has been deployed.

## Stage 1: prove a contract

Use the fixture-backed `get_ticket` tool and in-memory client. Evidence:
the known ticket is returned, a missing ID fails, and the result cannot mutate
the stored fixture accidentally.

This isolates the tool contract from process and network failures.

## Stage 2: add context and process isolation

Read `ticket://T-100`, obtain `summarize_ticket`, and run the same contracts
through stdio. Evidence: the child starts using the intended interpreter,
protocol stdout remains clean, and the client closes it.

No LLM is needed to verify these component contracts.

## Stage 3: add remote access

Use Streamable HTTP and verify both the endpoint and protocol era. Add
authentication before remote exposure, then verify permitted and denied
requests. Evidence includes wrong-path errors, scope denial, and wrong-tenant
rejection.

Introduce the proxy only when TLS/routing requirements justify it.

## Stage 4: make changes durable

Add an application service and repository for closing a ticket. Persist
operation identity and outcome. Evidence: restart preserves records,
concurrent changes respect the domain rule, and replay does not duplicate the
business action.

A database transaction handles related database writes. An external
notification needs its own reliable delivery design.

## Stage 5: add user interaction

Request a reason or approval with modern elicitation. Store or protect
continuation state and revalidate the caller on each round. Evidence: decline,
cancellation, missing input, changed permissions, stale ticket versions, and
replay all have defined outcomes.

The user experience should explain the target action precisely.

## Stage 6: operate and evolve

Add typed settings, owned lifespans, readiness, bounded concurrency, logs,
metrics, and traces. Containerize after the runtime and networking concepts
are understood. Evidence: shutdown is bounded, dependencies fail clearly,
telemetry can locate a slow call, and secrets do not enter logs or images.

```
Host --> MCP client --> HTTPS entry --> MCP application
                                           |
                                     ticket service
                                           |
                                     durable store
```

Add a gateway, cache, task extension, or interactive App only when a concrete
requirement cannot be met cleanly by this baseline.

## What the design buys

The same domain rules can be tested without MCP, exposed through MCP, and
operated behind HTTP. Each stage adds one reason for complexity and a way to
observe whether it works.

## Keep the first implementation small

The capstone begins with the same thin adapter used throughout the course:

```python
@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read one ticket by ID. Does not change it."""
    return ticket_service.get(ticket_id)
```

Later stages evolve `ticket_service`; they do not require JSON-RPC parsing in
the business layer. Add authorization, persistence, and idempotency where the
responsibility belongs, then keep the MCP handler focused on translation.

**Professional articulation:**

> “We grow the service by adding a requirement, identifying the baseline's
> failure, then implementing and verifying the smallest appropriate change.”

## Sources and next step

- [Complete synthetic lab](../labs/README.md)
- [Archived MCP walkthrough](../walk-through-docs/walkthrough_doc.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28) — checked 2026-11-15.

Return to the [course path](../README.md) or choose a concept to explore in depth.

