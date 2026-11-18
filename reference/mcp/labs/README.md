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

- [server.py](server.py): fixtures, ordinary lookup, tool, resource template,
  and reusable prompt.
- [client.py](client.py): checks through memory, stdio, or HTTP.
- [test_domain.py](test_domain.py): successful read, missing record, and
  accidental mutation protection.
- [test_protocol.py](test_protocol.py): missing argument and unknown-record
  failures through the MCP client.
- [continuation_model.py](continuation_model.py): dependency-free model of
  approval, caller isolation, and sequential replay.
- [verify_http.py](verify_http.py): starts a temporary server, verifies HTTP,
  and stops only its own process.
- [auth_calendar_server.py](auth_calendar_server.py): publishes OAuth Protected
  Resource Metadata, validates fake bearer tokens, filters tools by scope, and
  models a separate downstream calendar credential.
- [verify_auth_calendar.py](verify_auth_calendar.py): starts the calendar server
  and verifies discovery, authorization, direct-call denial, user isolation,
  and mock OBO.

## Run each boundary

```bash
uv run python -m unittest -v test_domain.py test_protocol.py
uv run python client.py memory
uv run python client.py stdio
uv run python continuation_model.py
uv run python verify_http.py
uv run python verify_auth_calendar.py
```

Expected results: three domain tests and two protocol tests pass; each client
mode reports `tool, resource, and prompt checks passed`; the domain model
reports its decline/identity/replay checks passed; and the calendar check
reports that discovery, private visibility, denial, user isolation, and mock
delegation passed.
Server diagnostics may also appear on stderr, separately from protocol stdout.

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

The calendar lab uses real MCP HTTP authorization middleware but fake token
records and a mock downstream credential broker. It is not a real authorization
server, Microsoft Entra OBO exchange, Google consent flow, or Calendar API. Read
[OAuth discovery](../concepts/20-oauth-discovery.md) and
[authorization](../concepts/21-authorization.md) for the production evolution.

## Diagnose the boundary

An import failure suggests a different environment. A subprocess failure
suggests an executable or path issue. HTTP refusal suggests no listener.
A binding-permission error comes from execution policy or local configuration.
A missing ticket is an application error. Inspect the corresponding boundary
before changing unrelated layers.
