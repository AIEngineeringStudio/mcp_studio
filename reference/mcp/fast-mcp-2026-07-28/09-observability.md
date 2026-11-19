# Lesson 9 — Observability and deprecated protocol logging

## Outcome

After this lesson, you can separate user-visible results from diagnostics and
choose logs, metrics, and traces for production evidence.

## Protocol logging is deprecated

MCP `2026-07-28` deprecates the protocol logging capability. It also removes
`logging/setLevel`. New implementations should use:

- ordinary process logging to `stderr` for stdio servers;
- structured application logs for operators;
- OpenTelemetry or an equivalent tracing system for cross-service work;
- metrics for rates, latency, saturation, and error counts.

The modern schema still contains `notifications/message` for compatibility.
Log preference is request-scoped through
`io.modelcontextprotocol/logLevel` in `_meta`; a server must not emit protocol
log notifications for a request that did not include that field.

Do not make deprecated protocol logging the primary observability design.

## Four audiences

```text
Tool result      -> model and user
Progress         -> user watching active work
Application log  -> operator diagnosing behavior
Audit event      -> security/compliance reviewer
```

One event can produce several records, but each record has a different
contract. A stack trace should not become model-visible tool content. A tool
result should not be your only audit record.

## Logs, metrics, and traces

**Logs:**

> Discrete structured events: what happened, at what severity, and with which
> safe correlation fields.

**Metrics:**

> Aggregated numeric signals: request rate, error rate, duration, queue depth,
> and resource saturation.

**Traces:**

> A tree of timed spans showing how one operation moved through MCP dispatch,
> business services, databases, and downstream APIs.

```text
tools/call span
  +-- authorization span
  +-- ticket-service span
  |     +-- database span
  +-- serialization span
```

The JSON-RPC request ID is not a trace ID. Use standard trace context and keep
business identifiers separate.

## Safe structured logging

Useful fields include:

- protocol revision and method;
- tool or component name;
- authenticated principal or pseudonymous subject ID;
- authorization decision;
- duration and outcome class;
- trace ID and deployment instance.

Avoid logging raw prompts, model output, access tokens, secrets, full tool
arguments, or sensitive resource content by default. Redact at the source; do
not rely only on downstream log filters.

## stdio rule

For a stdio MCP server, stdout carries protocol messages. Write diagnostic logs
to stderr. A stray `print()` to stdout can corrupt framing.

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("ticket lookup completed", extra={"tool": "get_ticket"})
```

## Failure classification

Keep at least these outcomes distinct:

- invalid MCP request;
- denied authorization;
- tool/domain error;
- dependency timeout or failure;
- cancellation;
- server defect.

This distinction makes alerts actionable and prevents expected user errors from
being reported as server incidents.

## Hands-on checkpoint

Run the lab over stdio and confirm that its protocol output remains separate
from diagnostics:

```bash
cd reference/mcp/labs
uv run python client.py stdio
```

Read
[`../concepts/28-observability.md`](../concepts/28-observability.md) for the
production evidence model.

**Say it professionally:**

> MCP protocol logging is deprecated. I keep model-visible results, user
> progress, operator telemetry, and security audit evidence as separate
> channels, correlated through standard trace context and safe identifiers.

## Official references

- [Key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [Schema reference](https://modelcontextprotocol.io/specification/2026-07-28/schema)
- [FastMCP OpenTelemetry](https://gofastmcp.com/docs/servers/telemetry)

