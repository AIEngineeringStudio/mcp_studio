# Continuation state and safe reentry

**Outcome:** Preserve a multi-round operation's context without trusting client-controlled state.

**Prerequisites:** [13: Elicitation and additional user input](13-elicitation.md).

## A local variable does not cross requests

A two-round workflow first selects a ticket category, then asks for approval.
When the second request arrives, the first handler invocation may no longer
exist. The server needs enough context to determine the next valid step.

Three choices are useful: recompute from authenticated data, store state on the
server under an opaque handle, or carry protected continuation state through
the client. Choose based on sensitivity, size, lifetime, and durability.

```
NEEDS_REASON --> NEEDS_APPROVAL --> APPLIED
                     |
                     +----------> NOT_APPLIED
```

A phase is an explicit state-machine position. It prevents accidentally
treating a reason response as an approval response.

## What requestState means

Modern MRTR can return an opaque `requestState` string that the client echoes
unchanged. The client must not interpret it, but a malicious client can still
tamper with bytes. The server must validate it.

Integrity protection detects changes. Encryption additionally hides content.
Neither alone guarantees that a valid message can be used only once. Bind
continuation to the authenticated principal, intended operation, relevant
arguments, and expiry; enforce single-use server-side when required.

## A concrete operation

The [simulation](../labs/continuation_model.py) stores an intent under
`op-1`, bound to Alice and T-100. It rejects Bob before returning even a
previously recorded result. It treats `accept` plus `approved=false` as no
action. Replaying Alice's successful operation returns its recorded outcome.

This is sequential, in-memory domain behavior. It does not survive restart,
implement atomic multi-process consumption, sign state, or handle an external
side effect transactionally. Those are explicit production extensions.

## Reentry requires a side-effect boundary

Separate “derive next input request” from “apply the mutation.” A handler that
sends email before checking for prior completion can send repeatedly as the
client retries. Persist the operation outcome or use the downstream service's
idempotency mechanism.

Recheck authorization on the later round. A user may lose access between
selection and approval. Also verify that the approved object and arguments
still match the action being applied.

## Expiration and changed data

If the ticket changes while the user considers the form, the server may need
a new confirmation. Include a version or comparison condition in the intent.
An expired continuation should fail clearly and allow a safe restart; it should
not continue with stale assumptions.

Keep continuation small. A whole report dataset is usually better stored
behind an authorized handle than encoded into every round.

**Professional articulation:**

> “Continuation state carries workflow context, not authority. Reentry
> revalidates identity, intent, and whether the action has already completed.”

## Sources and next step

- [Archive: conversations/chatgpt/83_Multi_round_elicitation.md](../../conversations/chatgpt/83_Multi_round_elicitation.md)
- [Archive: _learning_resources/enhancements.md](../../_learning_resources/enhancements.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr) — checked 2026-11-15.

Next: [Async I/O and concurrent requests](15-async-concurrency.md).

