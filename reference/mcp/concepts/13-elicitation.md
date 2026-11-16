# Elicitation and additional user input

**Outcome:** Explain how an MCP operation obtains missing information without inventing a user's answer.

**Prerequisites:** [04: Protocol versions and capability discovery](04-versions-discovery.md), [05: Tools and their contracts](05-tool-contracts.md).

## The missing-input problem

Suppose a ticket action needs a resolution reason. The original request
identified the ticket but omitted that reason. Guessing would create incorrect
business data. Elicitation lets the server ask the client to obtain additional
user input.

Modern MCP carries this interaction through a Multi Round-Trip Request
(MRTR). The server returns an input-required result. The client obtains the
requested input and reissues the original operation with responses.

```text
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

## Input collection versus permission

The user may supply “duplicate ticket” as a reason. The server still needs to
verify that the authenticated caller may close this ticket.

If the form asks for approval, distinguish the interaction outcome
`accept` from a business field such as `approved=true`. A successfully
submitted form can contain a negative decision. Decline, cancellation, missing
answers, and unsupported elicitation must all have deliberate behavior.

Never make a write before the necessary input and access checks have
succeeded. Otherwise reentry can repeat the write or apply it before the
user's decision.

## Design the form

Request only information needed by the operation. A small typed schema makes
valid responses clearer than an unconstrained paragraph. Avoid collecting
credentials in ordinary forms; credential workflows need an appropriate
secure authorization mechanism.

Include enough context for the person to understand the action: which ticket,
what will change, and any consequence. An unlabeled “Continue?” request is
weak evidence of informed intent.

## Observe the local model

Run the dependency-free [continuation simulation](../labs/continuation_model.py):

```bash
python3 reference/mcp/learning/labs/continuation_model.py
```

It demonstrates domain approval handling and repeat-call behavior. It is
explicitly not an MCP transport, real human approval UI, or OAuth implementation.
Guide 14 explains the state behind the repeated calls.

## When the host cannot ask

Capability support must be explicit. A server should not assume every host can
display a form. Depending on the operation, return a clear unsupported-feature
error or offer a documented alternative with explicit arguments. Do not
silently replace a required decision with a default approval.

**Professional articulation:**

> “Elicitation gathers missing user input. The service separately validates
> that input and authorizes the requested action.”

## Sources and next step

- [Archive: conversations/chatgpt/81_MCP_Elicitation.md](../../conversations/chatgpt/81_MCP_Elicitation.md)
- [Archive: conversations/auth/How_it_works.md](../../conversations/auth/How_it_works.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr) — checked 2026-11-15.

Next: [Continuation state and safe reentry](14-continuation-state.md).

