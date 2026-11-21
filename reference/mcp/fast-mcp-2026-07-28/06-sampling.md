# Lesson 6 — Sampling: deprecated model-borrowing pattern

## Outcome

After this lesson, you can explain why sampling was useful, why it is
deprecated, and how a modern server should obtain model inference.

## Status in this protocol revision

**Deprecated:**

> Sampling remains represented for compatibility, but new servers should call
> an LLM provider directly rather than borrowing the connected host's model.

Legacy sampling was a server-initiated request:

```
LEGACY MCP
tool handler -- sampling/createMessage --> client-owned model
tool handler <-- generated message -------- client
```

This coupled the tool to a live client back-channel. Modern MCP removed that
server-to-client request direction.

## Preferred modern design

```
MCP client -- tools/call --> MCP server -- provider SDK --> model provider
```

The server now owns:

- provider credentials and model selection policy;
- timeout, retry, cost, and rate limits;
- content policy and audit behavior;
- deterministic fallback when inference fails.

Keep model output away from authorization and correctness boundaries. A model
may classify or summarize; application code must still validate and authorize
the resulting action.

## MRTR compatibility form

When borrowing the caller's model is genuinely required, the modern protocol
represents the request as MRTR data:

```json
{
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
              "text": "Summarize ticket T-100."
            }
          }
        ],
        "maxTokens": 200
      }
    }
  },
  "requestState": "opaque-integrity-protected-state"
}
```

The client performs the inference and retries the original operation with a
new JSON-RPC request ID:

```json
{
  "name": "summarize_ticket",
  "arguments": {"ticket_id": "T-100"},
  "inputResponses": {
    "summary": {
      "role": "assistant",
      "content": {"type": "text", "text": "The ticket is open."},
      "model": "client-selected-model",
      "stopReason": "endTurn"
    }
  },
  "requestState": "opaque-integrity-protected-state"
}
```

The operation re-enters from the beginning. Design it as a state machine, not
as a suspended Python stack frame.

## Trust boundary

- Treat `inputResponses` and echoed `requestState` as untrusted.
- Protect continuation state with integrity protection such as AEAD or HMAC.
- Bind state to the authenticated principal, original operation, and expiry.
- Limit model rounds, tokens, time, and cost.
- Never execute a model-proposed tool call without normal authorization.

## Compatibility note for FastMCP

FastMCP 4 serves legacy and modern protocol eras, but the convenient legacy
server-initiated sampling API is not the design target for a modern-only
application. Use a provider SDK for new production code. Keep legacy exercises
in `../fast-mcp-2025-11-25/` clearly labeled.

## Server-owned provider code

This concept exercise injects a deterministic provider. A production extension
would replace it with the chosen provider SDK, credentials, timeout, retry, and
cost policy.

```python
from typing import Protocol


class SummaryProvider(Protocol):
    async def summarize(self, text: str) -> str: ...


async def summarize_ticket(
    ticket_id: str,
    provider: SummaryProvider,
) -> str:
    return await provider.summarize(f"Ticket {ticket_id} is open.")
```

The MCP handler owns or receives the provider dependency. It does not send a
`sampling/createMessage` request to the connected client.

## Hands-on checkpoint

**Execution boundary:**

> In-memory MCP with a deterministic fake downstream provider. There is no
> client sampling request, model account, external API, or secret.

Run the deterministic provider-boundary exercise from the repository root. It
uses no model account, network API, or secret:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_sampling_boundary.py
```

Expected output:

```
sampling replacement: the MCP server called its own provider
no sampling/createMessage request was sent to the client
```

The complete runnable exercise is
[`verify_sampling_boundary.py`](../labs/verify_sampling_boundary.py).

**Say it professionally:**

> Sampling borrowed inference from the connected MCP client. Because that
> back-channel is deprecated, modern servers normally integrate directly with
> a model provider; MRTR is reserved for explicit client-owned input flows.

## Official references

- [Key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [MRTR](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [FastMCP 4 announcement](https://blog.gofastmcp.com/3mufbh2vcv22o)

