# Testing and debugging MCP by layer

**Outcome:** Choose checks that isolate the failing boundary and prove the intended behavior.

**Prerequisites:** [07: The first client and in-memory testing](07-in-memory-client.md), [08: stdio and subprocess boundaries](08-stdio-processes.md), [11: Streamable HTTP](11-streamable-http.md), [21: Authorization, scopes, and tenant isolation](21-authorization.md).

## A healthy process can still serve a broken tool

Testing should follow the responsibility boundaries already introduced.

```
domain rules --> repository --> MCP contracts --> transport --> host workflow
```

Each check proves a different property. A unit test cannot establish TLS
configuration. A successful HTTP status cannot establish tenant isolation.

## Run the supplied checks

After [lab setup](../fast-mcp-2026-07-28/labs/README.md), run these from the lab directory:

```bash
uv run python -m unittest -v test_domain.py test_protocol.py
uv run python client.py memory
uv run python client.py stdio
uv run python continuation_model.py
```

The HTTP check uses the two-terminal procedure in guide 11. The
[validation record](../VALIDATION.md) states which combinations actually ran.

The domain tests check a successful lookup, a missing ID, and protection from
accidental mutation of fixture state. The client checks observable tool,
resource, and prompt behavior. The continuation simulation checks denial,
identity isolation, and sequential replay.

Two negative protocol tests verify that missing arguments and an unknown
record surface as tool errors. Each transport client also asserts the modern
protocol revision, so a silent fallback to legacy behavior fails visibly.

## Add failures that matter

For a production extension, test invalid types, missing required arguments,
unknown component names, insufficient scopes, another tenant's record,
disconnects, and duplicate submissions. Verify that denied writes caused no
side effect.

Do not disable all authorization and then describe the resulting in-memory
test as a security test. A test double can isolate business logic, but the
real authentication/authorization path needs its own test.

## Diagnose in order

If the client cannot start a child, inspect the executable, path, environment,
and stderr. If HTTP cannot connect, inspect listener and route. If discovery
works but invocation fails, compare the discovered schema and provided
arguments. If a valid invocation returns wrong data, inspect the service and
repository.

For streaming issues, compare emission time, proxy behavior, and client
consumption. For multi-round behavior, record phase and operation identity
without logging sensitive user answers.

## Host behavior is another layer

A scripted client bypasses model tool selection. A host integration test
should verify that the intended tool is offered, a permitted call occurs, and
the result is interpreted accurately. Use deterministic assertions where
possible and representative evaluations for model-dependent behavior.

## A useful regression

Rename a tool in a temporary exercise and observe that the catalog assertion
fails. This proves that the client contract check detects a meaningful breaking
change. Restore the name after the experiment.

**Professional articulation:**

> “We test each boundary for the behavior it owns, then use a small number of
> end-to-end checks to verify composition.”

## Sources and next step

- [Archived testing and tracing example](../fastMcp-fastApi-uvicorn-ngnix-docker/11_AutomatedTests_Metrics_DistributedTracing.md)
- [Archived observability notes](../fast-mcp/2026-07-28/11-observability.md)
- [Official reference](https://gofastmcp.com/docs/clients/client) — checked 2026-11-15.

Next: [Logs, metrics, and traces](28-observability.md).

