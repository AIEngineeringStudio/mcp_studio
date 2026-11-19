# Logs, metrics, and traces

**Outcome:** Select operational evidence that explains a slow or failed tool call.

**Prerequisites:** [18: Uvicorn, workers, and process state](18-process-runtime.md), [27: Testing and debugging MCP by layer](27-testing.md).

## Three questions, three signals

A log records an event. A metric measures a quantity across events. A trace
connects timed work across a request path.

| Signal | Useful question |
|---|---|
| Log | What failed during this operation? |
| Metric | How often are calls failing? |
| Trace | Which dependency consumed the time? |

These signals complement software tests. Tests examine chosen conditions;
telemetry describes actual runtime behavior.

## Trace the ticket lookup

```
host operation
    +-- MCP call
          +-- authorize
          +-- repository read
          +-- result serialization
```

A span describes one timed unit of work. A trace ID connects spans. A request
ID may correlate a single protocol exchange, while a business operation ID can
connect several retries or input rounds. Choose names that make this scope
clear.

Do not depend on Python globals to hold the current trace or caller across
concurrent requests.

## Useful initial measurements

Measure request rate, latency distribution, error categories, and active
operations. Add pool-wait time or upstream latency when those dependencies
exist. A high average latency can hide a small but important tail of very slow
requests, so inspect percentiles and distributions.

Label metrics with bounded categories such as tool name and outcome. User
IDs, ticket IDs, and arbitrary error text create high cardinality: too many
distinct time series to store and query efficiently.

## Privacy and protocol safety

Logs should not contain bearer tokens or unnecessary ticket content. Use safe
error classes and correlation identifiers. In stdio, send application
diagnostics to stderr so they cannot corrupt the protocol stream.

A dashboard trace bus in the archive is application infrastructure. Its UI
events are not necessarily MCP messages. The same applies to model “thinking”
visualizations: expose meaningful supported activity, not invented internal
reasoning.

## Exporters and failure modes

Instrumentation can produce no externally visible trace until an SDK/exporter
is configured. Verify that a known request appears in the intended backend.
Also verify that an unavailable telemetry backend does not unexpectedly make
the ticket service unusable.

A process-local event list is adequate for a demo but cannot serve as durable
cross-worker observability. Bound memory and define loss behavior.

## Worked diagnosis

Calls take two seconds. The trace shows 1.8 seconds waiting for a database
connection and only 20 milliseconds executing the query. Optimizing JSON
serialization would target the wrong bottleneck. Investigate pool sizing,
long-held connections, and database capacity.

## Record a useful event without the ticket body

```python
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket_service")

event = {
    "event": "tool_completed",
    "tool": "get_ticket",
    "request_id": "rpc-17",
    "outcome": "success",
    "duration_ms": 24,
}
logger.info(json.dumps(event))
```

The event records a bounded tool name, outcome, correlation ID, and duration.
It omits the bearer token and ticket contents. In a `stdio` server, configure
application logging to use stderr so it cannot corrupt protocol stdout.

**Professional articulation:**

> “Metrics reveal the pattern, traces locate the delay, and logs explain
> individual failures without exposing sensitive payloads.”

## Sources and next step

- [Archived testing and tracing example](../fastMcp-fastApi-uvicorn-ngnix-docker/11_AutomatedTests_Metrics_DistributedTracing.md)
- [Archived observability notes](../fast-mcp/09-observability.md)
- [Official reference](https://opentelemetry.io/docs/concepts/signals/) — checked 2026-11-15.

Next: [Scaling and MCP gateways](29-scaling-gateways.md).

