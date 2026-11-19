# Elicitation and additional user input

**Outcome:** Explain how a modern MCP operation obtains missing information,
handles the user's response deliberately, and avoids treating input as
permission.

**Prerequisites:**
[04: Protocol versions and capability discovery](04-versions-discovery.md) and
[05: Tools and their contracts](05-tool-contracts.md).

## The missing-input problem

Suppose a ticket action needs a resolution reason. The original request
identified the ticket but omitted that reason. Guessing would create incorrect
business data. Elicitation lets the server ask the client to obtain additional
user input.

Modern MCP carries this interaction through a Multi Round-Trip Request
(MRTR). The server returns an input-required result. The client obtains the
requested input and reissues the original operation with responses.

**Multi Round-Trip Request (MRTR):**

> A modern MCP interaction in which one logical operation needs more than one
> client request. Each round trip is a complete request and result; the server
> does not rely on one suspended Python call stack.

**Input-required result:**

> A result with `resultType="input_required"` that describes the additional
> information needed before the operation can complete.

**Input response:**

> The user's supplied answer carried in the next request. That request uses a
> new JSON-RPC request ID and can echo opaque continuation state supplied by the
> server.

```
Client                          Server
  | ---- close ticket ----------> |
  | <--- input required: reason - |
  |                               |
  +---- obtain user input         |
  |                               |
  | ---- retry with response ---->|
  | <--- completed result --------|
```

The resumed operation is a new request. Do not assume a suspended Python stack
survives between rounds. Legacy examples using a server request and a waiting
coroutine describe a different protocol era.

```text
Legacy through 2025-11-25: server sends elicitation/create during a live call
Modern 2026-07-28:         server returns input_required; client sends a new call
```

## Input collection versus permission

The user may supply “duplicate ticket” as a reason. The server still needs to
verify that the authenticated caller may close this ticket.

If the interaction asks for approval, distinguish the interaction outcome
`accept` from a business field such as `approved=true`. A successfully
submitted response can contain a negative decision. Decline, cancellation, missing
answers, and unsupported elicitation must all have deliberate behavior.

Never make a write before the necessary input and access checks have
succeeded. Otherwise reentry can repeat the write or apply it before the
user's decision.

## Handle every interaction outcome

**Accept:**

> The user submitted input. Validate its structure, then apply normal business
> validation and authorization. Acceptance of the interaction is not automatic
> approval of the business action.

**Decline:**

> The user explicitly rejected the request for input or the proposed action.
> Stop or use only a safe, documented alternative.

**Cancel:**

> The interaction ended without an explicit yes or no. Do not reinterpret
> cancellation as acceptance.

**Missing or invalid response:**

> Return another controlled input requirement or fail clearly. Do not invent a
> value that changes business data.

## Design the input request

Request only information needed by the operation. A small typed schema makes
valid responses clearer than an unconstrained paragraph. Avoid collecting
credentials in ordinary forms; credential workflows need an appropriate
secure authorization mechanism.

Include enough context for the person to understand the action: which ticket,
what will change, and any consequence. An unlabeled “Continue?” request is
weak evidence of informed intent.

The input schema describes shape, such as a required reason string. Application
code must still reject a stale ticket, an unauthorized caller, or a reason that
violates business rules.

## Observe the local model

Run the dependency-free [continuation simulation](../labs/continuation_model.py):

```bash
python3 reference/mcp/labs/continuation_model.py
```

It demonstrates domain approval handling and repeat-call behavior. It is
explicitly not an MCP transport, real human approval UI, or OAuth implementation.
Guide 14 explains the state behind the repeated calls.

## Failure behavior belongs in the contract

**Host lacks input support:**

> Return a clear unsupported-feature result or use a documented alternative
> input path. Capability support must be explicit; never assume approval.

**User never responds:**

> Expire the continuation after a bounded period and allow a safe restart. Do
> not retain unlimited pending operations.

**Input arrives after business data changed:**

> Revalidate current data and, when needed, request confirmation again. The
> earlier input does not freeze the ticket's state.

**Professional articulation:**

> “Elicitation gathers missing user input. The service separately validates
> that input and authorizes the requested action.”

## Sources and next step

- [Archived elicitation example](../fastMcp-fastApi-uvicorn-ngnix-docker/81_MCP_Elicitation.md)
- [Archived authorization flow](../auth/How_it_works.md)
- [Legacy response-action and failure explanations](../elicitation/chunk-5.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)

Next: [Continuation state and safe reentry](14-continuation-state.md).

