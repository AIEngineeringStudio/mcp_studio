# MCP concept labs

These complete source files implement a synthetic ticket service and a
synthetic calendar authorization boundary. No model, real credential, database,
Docker, calendar account, or external business API is needed.
Read [the version baseline](../VERSIONS.md) for the tested runtime and limits.

## Workspace-local setup

From the project root, run these commands in order:

```bash
cd reference/mcp/labs
export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
uv sync --locked --python 3.14.3
```

These exports keep package caches and downloaded Python inside this folder.
The virtual environment and caches are ignored by Git. Use the same exports
in another terminal before running lab commands there. Both Mac architectures
use the same commands; only Intel macOS was executed. Native packages may need
compatible wheels or build tools on Apple Silicon.

If `uv` is missing, use the workspace environment lesson to configure it.
This course does not install global tools. The lockfile fixes dependency
resolution for this concept snapshot.

## Source files

- **Core service:** [server.py](server.py), [client.py](client.py),
  [test_domain.py](test_domain.py), and [test_protocol.py](test_protocol.py).
- **Modern request model:**
  [client.py](lesson_1/client.py),
  [verify_primitives.py](verify_primitives.py), and
  [compare_protocol_eras.py](compare_protocol_eras.py).
- **Deprecated-feature replacements:**
  [verify_modern_roots_replacement.py](verify_modern_roots_replacement.py) and
  [verify_sampling_boundary.py](verify_sampling_boundary.py).
- **Request behavior:** [continuation_model.py](continuation_model.py),
  [verify_progress.py](verify_progress.py),
  [verify_pagination_completion.py](verify_pagination_completion.py), and
  [verify_context_lifespan.py](verify_context_lifespan.py).
- **FastMCP architecture:** [verify_middleware.py](verify_middleware.py) and
  [verify_composition.py](verify_composition.py).
- **Transport and operations:** [logging_server.py](logging_server.py),
  [verify_observability.py](verify_observability.py),
  [verify_http.py](verify_http.py),
  [transport_security_server.py](transport_security_server.py), and
  [verify_transport_security.py](verify_transport_security.py).
- **Authorization:** [auth_calendar_server.py](auth_calendar_server.py) and
  [verify_auth_calendar.py](verify_auth_calendar.py).

## Run each boundary

The lesson checkpoints use three execution boundaries:

- **In-memory MCP:** protocol and FastMCP behavior without a child process or
  network port.
- **stdio:** a client-managed child process using stdin/stdout for protocol
  traffic and stderr for diagnostics.
- **Streamable HTTP:** temporary loopback servers for transport,
  authorization, and Host/Origin checks.

`continuation_model.py` has no MCP transport, and the cursor portion of
`verify_pagination_completion.py` is a plain-Python application model. Their
lessons label those limits explicitly.

```bash
uv run python -m unittest -v test_domain.py test_protocol.py
uv run python client.py --transport stdio
uv run python verify_primitives.py tools
uv run python verify_primitives.py resources
uv run python verify_primitives.py prompts
uv run python verify_modern_roots_replacement.py
uv run python verify_sampling_boundary.py
uv run python continuation_model.py
uv run python verify_progress.py
uv run python verify_observability.py
uv run python verify_pagination_completion.py
uv run python verify_context_lifespan.py
uv run python verify_middleware.py
uv run python verify_composition.py
uv run python compare_protocol_eras.py
uv run python client.py memory
uv run python client.py stdio
uv run python verify_http.py
uv run python verify_auth_calendar.py
uv run python verify_transport_security.py
```

Each command prints the specific behavior it verified. Three domain tests and
two negative protocol-contract tests pass. HTTP checks use only loopback ports
and stop only the child process they started. Server diagnostics may appear on
stderr, separately from protocol stdout.

For the manual HTTP flow, use two terminals in this directory:

```bash
# Terminal 1
uv run python server.py --http
```

```bash
# Terminal 2
uv run python client.py http
```

Stop terminal 1 with Ctrl-C. Port 8765 must be free. `verify_http.py` refuses
to run if it is occupied and never stops an existing service.

## What the client demonstrates

It lists tools, calls `get_ticket`, reads `ticket://T-100`, and retrieves
`summarize_ticket`. Prompt retrieval does not invoke a model. Memory mode
imports the server; stdio launches it; HTTP connects to a running service.
The client also asserts that the negotiated protocol is `2026-07-28`.

The continuation simulation is not MCP wire code or a real approval UI. It is
sequential and in-memory. Durable storage, atomic consumption, signed state,
OAuth, and actual MRTR callbacks are separate implementation exercises.

The pagination helper is an application-level cursor model; its completion
check uses the real MCP API. The sampling replacement uses a deterministic fake
provider, not a live model. Middleware, composition, progress, lifespan, and
protocol-era checks use real FastMCP client/server calls in memory.

The calendar lab uses real MCP HTTP authorization middleware but fake token
records and a mock downstream credential broker. It is not a real authorization
server, Microsoft Entra OBO exchange, Google consent flow, or Calendar API. Read
[OAuth discovery](../../../concepts/20-oauth-discovery.md) and
[authorization](../../../concepts/21-authorization.md) for the production evolution.

## Diagnose the boundary

An import failure suggests a different environment. A subprocess failure
suggests an executable or path issue. HTTP refusal suggests no listener.
A binding-permission error comes from execution policy or local configuration.
A missing ticket is an application error. Inspect the corresponding boundary
before changing unrelated layers.
