# Lesson 7 — Elicitation through multi-round requests

## Outcome

After this lesson, you can trace an elicitation request, distinguish
`input_required` from a final result, and design retry-safe continuation state.

## Why elicitation exists

A tool sometimes discovers missing information only after it starts. The
server must not invent the user's answer.

```
call operation
     |
     +-- enough input --> complete
     |
     +-- missing input -> input_required -> client asks user -> retry
```

MCP `2026-07-28` uses Multi Round-Trip Requests (MRTR). The server returns the
question as data instead of sending a nested JSON-RPC request to the client.

## Round 1: server requests input

The repeated request `_meta` is omitted here for readability.

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/call",
  "params": {
    "name": "close_ticket",
    "arguments": {"ticket_id": "T-100"}
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "approval": {
        "method": "elicitation/create",
        "params": {
          "mode": "form",
          "message": "Approve closing ticket T-100?",
          "requestedSchema": {
            "type": "object",
            "properties": {
              "approved": {"type": "boolean"}
            },
            "required": ["approved"]
          }
        }
      }
    },
    "requestState": "opaque-integrity-protected-state"
  }
}
```

## Round 2: client retries the original request

The retry uses a new JSON-RPC ID because it is a new request:

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "method": "tools/call",
  "params": {
    "name": "close_ticket",
    "arguments": {"ticket_id": "T-100"},
    "inputResponses": {
      "approval": {
        "action": "accept",
        "content": {"approved": true}
      }
    },
    "requestState": "opaque-integrity-protected-state"
  }
}
```

The terminal response uses `resultType: "complete"`.

## Guard-pattern implementation model

```
start operation
  |
  +-- no response ------> return InputRequiredResult
  |
  +-- decline/cancel ---> return a safe terminal result
  |
  +-- accept -----------> re-authorize, apply once, return complete
```

The server may receive the operation more than once. Put side effects after the
guard, make them idempotent, and store a server-controlled operation key when
exactly-once business behavior matters.

`requestState` is opaque to the client, but the client transports it. Protect
its integrity and bind it to identity, operation, and expiry. Do not put
secrets or large application objects in it.

## Form mode and URL mode

Use form mode for non-secret structured input. Avoid requesting passwords,
private keys, or raw access tokens in a model-visible form.

URL mode sends the user to an external interaction. It is not a replacement for
MCP OAuth, and the return path still needs correlation, expiry, and replay
protection.

## Requests allowed to use MRTR

Only these core requests may return `InputRequiredResult`:

- `tools/call`;
- `resources/read`;
- `prompts/get`.

Other methods must not return this result type.

## Hands-on checkpoint

The repository includes a protocol-independent state-machine exercise that
proves decline handling, identity isolation, and replay safety:

```bash
cd reference/mcp/labs
uv run python continuation_model.py
```

Then read
[`../concepts/13-elicitation.md`](../concepts/13-elicitation.md) and
[`../concepts/14-continuation-state.md`](../concepts/14-continuation-state.md).

**Say it professionally:**

> Modern elicitation is a multi-round state machine. The server returns an
> `input_required` result, the client gathers input, and the client retries the
> original operation with a new request ID and explicit continuation data.

## Official references

- [MRTR](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)
- [FastMCP elicitation](https://gofastmcp.com/servers/elicitation)

