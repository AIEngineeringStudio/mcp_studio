# MCP Apps Learning

This project contains small, runnable lessons for learning how an MCP server
can return data and connect a tool to an interactive MCP App resource.

## Lessons

### Lesson 1 — Understand the MCP App mental model

Learn the roles of the MCP host, client, server, tool, resource, and user
interface before adding implementation details.

### Lesson 2 — Register a tool and its MCP App resource

File: `mcp_apps_learning/lessons/register_tool_resource/server.py`

This server demonstrates the smallest MCP App flow:

1. A client calls the `say_hello` tool.
2. The tool returns a text result.
3. The tool points to an HTML resource through its `resource_uri`.
4. The MCP host can render that resource as the tool's user interface.

### Lesson 3 — Return structured data from a tool

File: `mcp_apps_learning/lessons/structured_data/server.py`

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

The `mcp-apps` PyProject command is the recommended way to run these lessons.

| Command                             | Server                 |
|-------------------------------------|------------------------|
| `uv run --locked mcp-apps`          | Hello server (default) |
| `uv run --locked mcp-apps hello`    | Hello server           |
| `uv run --locked mcp-apps customer` | Customer server        |

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
uv run --locked mcp dev \
  mcp_apps_learning/lessons/register_tool_resource/server.py
```

For the structured-data lesson:

```shell
uv run --locked mcp dev mcp_apps_learning/lessons/structured_data/server.py
```

Use Inspector to list the available tools, call a tool, and inspect its result
and associated MCP App resource.

## Run through the MCP CLI

The PyProject command above is shorter for everyday use. You can also run a
server file explicitly through the MCP CLI:

```shell
uv run --locked mcp run \
  mcp_apps_learning/lessons/register_tool_resource/server.py \
  --transport streamable-http
```

```shell
uv run --locked mcp run mcp_apps_learning/lessons/structured_data/server.py \
  --transport streamable-http
```

## Project structure

```text
mcp-apps-learning/
├── mcp_apps_learning/
│   ├── cli.py
│   ├── registry.py
│   └── lessons/
│       ├── register_tool_resource/
│       │   └── server.py
│       └── structured_data/
│           └── server.py
├── pyproject.toml
└── uv.lock
```

- `mcp_apps_learning/cli.py` implements the `mcp-apps` launcher.
- `mcp_apps_learning/registry.py` maps short lesson names to server modules.
- Every directory under `mcp_apps_learning/lessons/` owns one lesson server.
- `pyproject.toml` defines dependencies, packaging, and runnable commands.
- `uv.lock` records the exact resolved dependency versions.

## Add another lesson

Use the same small pattern for each new lesson:

1. Create `mcp_apps_learning/lessons/<lesson_name>/`.
2. Add an empty `__init__.py` file.
3. Add `server.py` containing the lesson's `mcp` server and a `main()` function.
4. Add one entry to `LESSONS` in `mcp_apps_learning/registry.py`.
5. Run the lesson with `uv run --locked mcp-apps <lesson_name>`.

The shared launcher discovers every server through the registry. New lesson
packages do not need to be added to the build configuration because they live
under the existing `mcp_apps_learning` package. The single `mcp-apps` command
also means `pyproject.toml` does not grow as lessons are added.

## Professional articulation

This project exposes each MCP lesson as a separate server behind one shared
command-line launcher. A central registry makes new lessons discoverable, and
the lockfile keeps the learning environment reproducible.
