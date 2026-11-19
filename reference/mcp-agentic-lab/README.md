# MCP Agentic Lab

A reusable Python repository for learning the Model Context Protocol (MCP),
tool-calling agents, structured logging, distributed tracing, and JSON-RPC wire behavior.
It targets the official MCP Python SDK v2 and supports both stdio and Streamable HTTP.

## Included

- MCP tools, a resource, and a prompt
- stdio and Streamable HTTP server/client modes
- exact stdio JSON-RPC capture in both directions
- Streamable HTTP request/response body capture
- transport-neutral client and server semantic recording
- structured logs with trace/span correlation
- OpenTelemetry console or OTLP export
- provider-neutral plan/act/observe agent loop
- tests and progressive practice exercises

## Quick start

```bash
cd /Users/sreedhar/Desktop/codebases/mcp-agentic-lab
cp .env.example .env
uv sync --all-extras
uv run mcp-lab-client
uv run mcp-lab-agent "Add 7 and 8"
uv run pytest
```

The default client launches the server over stdio through a transparent wiretap.
Generated records live in `var/` and are ignored by git.

```bash
jq . var/wire.jsonl
jq 'select(.direction == "client_to_server")' var/wire.jsonl
```

## Streamable HTTP

Start the server in one terminal:

```bash
MCP_LAB_SERVER_TRANSPORT=streamable-http uv run mcp-lab-server
```

Then use either example over HTTP:

```bash
uv run mcp-lab-client --url http://127.0.0.1:8000/mcp
uv run mcp-lab-agent --url http://127.0.0.1:8000/mcp "Add 20 and 22"
```

## Observation layers

| File | Layer | Transports |
|---|---|---|
| `var/wire.jsonl` | exact newline-delimited JSON-RPC proxy | stdio |
| `var/http-wire.jsonl` | HTTP JSON-RPC request/response bodies | Streamable HTTP |
| `var/client-wire.jsonl` | decoded SDK operations and typed results | both |
| `var/server-wire.jsonl` | decoded server method, result, duration, errors | both |

Records are JSON Lines so they can be tailed and streamed. Common secret-bearing
keys are recursively redacted. Add domain-specific keys before recording real data.

Important: stdout is reserved for protocol traffic in stdio mode. Server logs are
always sent to stderr.

## Tracing

The official MCP SDK creates MCP spans automatically. This project installs the
OpenTelemetry provider that exports them and injects active trace IDs into logs.

```bash
# Local console spans (default)
MCP_LAB_TRACE_EXPORTER=console uv run mcp-lab-client

# OTLP collector
uv sync --extra otlp
MCP_LAB_TRACE_EXPORTER=otlp \
MCP_LAB_OTLP_ENDPOINT=http://localhost:4317 \
uv run mcp-lab-client
```

## Inspector and checks

```bash
uv run mcp dev src/mcp_lab/server/app.py
make check
```

## Adding a real model

Implement `AgentModel` in `mcp_lab.agent.core`. It receives the conversation and
the MCP-derived tool schemas, and returns either `ToolCall` or `FinalAnswer`.
This deliberate adapter boundary keeps the agent loop independent of a model vendor.

For a complete novice-to-expert walkthrough, use the
[teaching and learning guide](docs/learning-guide.md). It explains every module,
the stdio and HTTP code flows, JSON-RPC traffic, observability layers, agent loop,
guided labs, mastery checks, and production design considerations.

The shorter [practice exercises](docs/exercises.md) and
[architecture notes](docs/architecture.md) are useful as quick references.

