# Scaling and MCP gateways

**Outcome:** Add routing and shared infrastructure only when requirements justify their cost.

**Prerequisites:** [18: Uvicorn, workers, and process state](18-process-runtime.md), [21: Authorization, scopes, and tenant isolation](21-authorization.md), [25: Timeouts, cancellation, retries, and idempotency](25-reliability.md), [28: Logs, metrics, and traces](28-observability.md).

## First identify the limiting resource

Scaling can mean more users, larger catalogs, slower dependencies, or many
teams owning servers. Those pressures need different designs. Measure the
current bottleneck before adding replicas, caches, or a gateway.

A gateway is an intermediary that presents a controlled entry point to one or
more services. It can route tools, normalize names, apply broad policy, and
collect operational evidence.

```
Host --> gateway ----> ticket server --> ticket store
                |
                +----> document server --> document store
```

The gateway is another failure and trust boundary. It does not eliminate the
backend service's responsibility for record-level access.

## Names and authority

Two servers might both expose `search`. A gateway needs a stable naming or
routing rule so clients know which contract they are invoking. Keep result
and error meanings clear when forwarding.

A gateway credential with broad privileges must not turn every caller into
an administrator. Propagate verified identity or use an appropriate scoped
delegation arrangement, then enforce the actual target permissions.

## State ownership before replicas

Modern self-contained MCP requests reduce dependence on protocol sessions.
They do not remove application state. A pending operation, idempotency record,
or durable task must remain accessible when a retry reaches another replica.

Legacy sessions may require affinity or another session design. Do not carry
legacy sticky-session requirements into a modern design without checking
which state actually needs locality.

## Admission control

A slow dependency can accumulate thousands of active requests. Bound
concurrency, queue length, and operation duration. Rate limits constrain request
arrival; concurrency limits constrain simultaneous work. They solve different
problems.

A circuit breaker temporarily rejects calls to a failing dependency so that
the system can recover. Define what users see and when probing resumes.
A breaker is not a substitute for capacity planning.

## Avoid speculative infrastructure

A small local ticket tool needs no Redis, gateway, or orchestration cluster.
Add shared storage when multiple workers need durable state. Add caching when
measurement shows repeated authorized reads dominate cost. Add a gateway when
central routing or governance is a real requirement.

The archive's performance multipliers and named-company stories are not
benchmarks for this service. Establish a workload and measure your own system.

**Worked decision:**

> If three teams maintain independent servers, a gateway may simplify discovery.
> If one tool is slow because its SQL lacks an index, a gateway adds another
> hop without fixing the query.

**Professional articulation:**

> “We scale the measured bottleneck and preserve explicit ownership of
> identity, business state, and operation outcomes across replicas.”

## Sources and next step

- [Archive: conversations/auth/01-Secure-MCP-gateway.md](../../conversations/auth/01-Secure-MCP-gateway.md)
- [Archive: conversations/chunks/04-mcp-chunk4.md](../../conversations/chunks/04-mcp-chunk4.md)
- [Archive: conversations/streamable/streamable-6.md](../../conversations/streamable/streamable-6.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) — checked 2026-11-15.

Next: [Optional extensions and deprecated features](30-extensions.md).

