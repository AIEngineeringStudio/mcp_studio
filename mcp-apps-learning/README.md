# MCP Apps Learning

This project contains small, runnable lessons for learning how an MCP server
can return data and connect a tool to an interactive MCP App resource.

## Lessons

### Lesson 1 — Understand the MCP App mental model

Learn the roles of the MCP host, client, server, tool, resource, and user
interface before adding implementation details.

### Lesson 2 — Register a tool and its MCP App resource

File: `register_tool_MCP_App_resource/server.py`

This server demonstrates the smallest MCP App flow:

1. A client calls the `say_hello` tool.
2. The tool returns a text result.
3. The tool points to an HTML resource through its `resource_uri`.
4. The MCP host can render that resource as the tool's user interface.

### Lesson 3 — Return structured data from a tool

File: `structured_data_from_tool/customer_server.py`

This server returns a Pydantic `Customer` model. Structured data gives the
client named fields—`name`, `company`, and `email`—instead of one unstructured
text value.

## Prerequisites

- Python 3.14 or later
- [`uv`](https://docs.astral.sh/uv/) for dependency and environment management

The same setup and commands work on Intel and Apple Silicon Macs.

## Set up the project

From the repository root:

```shell
cd mcp-apps-learning
uv sync --locked
```

`uv sync --locked` creates or updates the virtual environment using the exact
versions recorded in `uv.lock`. It also installs the commands declared in the
`[project.scripts]` section of `pyproject.toml`.

## Run a lesson server

The PyProject commands are the recommended way to run these lessons.

| Command                             | Server                   |
|-------------------------------------|--------------------------|
| `uv run --locked mcp-apps`          | Hello server (default)   |
| `uv run --locked mcp-apps hello`    | Hello server             |
| `uv run --locked mcp-apps customer` | Customer server          |
| `uv run --locked hello-server`      | Hello server directly    |
| `uv run --locked customer-server`   | Customer server directly |

The servers use the **Streamable HTTP** transport by default. Stop a running
server with <kbd>Control</kbd>+<kbd>C</kbd> before starting another server on
the same default port.

### Choose a different transport

The main launcher accepts `stdio`, `sse`, or `streamable-http`:

```shell
uv run --locked mcp-apps customer --transport stdio
```

Use `stdio` when an MCP client starts the server as a child process and
communicates through standard input and output.

## Test with MCP Inspector

`mcp dev` starts MCP Inspector and connects to the selected server over
`stdio`:

```shell
uv run --locked mcp dev register_tool_MCP_App_resource/server.py
```

For the structured-data lesson:

```shell
uv run --locked mcp dev structured_data_from_tool/customer_server.py
```

Use Inspector to list the available tools, call a tool, and inspect its result
and associated MCP App resource.

## Run through the MCP CLI

The PyProject commands above are shorter for everyday use. You can also run a
server file explicitly through the MCP CLI:

```shell
uv run --locked mcp run register_tool_MCP_App_resource/server.py \
  --transport streamable-http
```

```shell
uv run --locked mcp run structured_data_from_tool/customer_server.py \
  --transport streamable-http
```

## Project structure

```text
mcp-apps-learning/
├── main.py
├── mcp_apps_learning/
│   └── cli.py
├── register_tool_MCP_App_resource/
│   └── server.py
├── structured_data_from_tool/
│   └── customer_server.py
├── pyproject.toml
└── uv.lock
```

- `main.py` provides a file-based compatibility entry point.
- `mcp_apps_learning/cli.py` implements the `mcp-apps` launcher.
- Each lesson directory owns its server implementation.
- `pyproject.toml` defines dependencies, packaging, and runnable commands.
- `uv.lock` records the exact resolved dependency versions.

## Professional articulation

This project exposes each MCP lesson as a separate server while providing one
shared command-line launcher. PyProject entry points give the servers stable
commands, and the lockfile keeps the learning environment reproducible.
