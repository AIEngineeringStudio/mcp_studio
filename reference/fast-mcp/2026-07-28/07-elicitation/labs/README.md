# Elicitation lab: process a batch, then ask the user

This small lab shows how an MCP tool can make progress, ask for more input, and
continue. The rows are **simulated**: each row is an `asyncio.sleep(0.2)`, and
no database or file is changed.

The client starts with a batch size of 4. After those four rows, the server asks
how many rows to process next. Enter a number from 1 to 10 to continue, or `0`
to finish.

## Run it

From the `mcp_studio_labs` project root, install the dependencies with
`uv sync`. The project pins **Python 3.14** and **FastMCP 4.2.0** in
`pyproject.toml`.

Then run the simplest version:

```bash
cd 07-elicitation/labs
uv run python client.py --transport in-memory --example elicitation
```

Try entering `2`, then `0`. You should see four progress messages, then two
more, then `Total rows processed: 6`.

For a separate server process that communicates over standard input and output:

```bash
uv run python client.py --transport stdio --example elicitation
```

The client starts `server.py` for you in this mode. For HTTP, start the server
in one terminal and the client in another, both from `07-elicitation/labs`:

```bash
# Terminal 1
uv run python server.py --transport http
```

```bash
# Terminal 2
uv run python client.py --transport http --example elicitation
```

The HTTP address is fixed in the code as `http://127.0.0.1:8000/mcp`. If the
port is occupied, change the port in `server.py` and `SERVER_URL` in `client.py`
together.

## What each file does

| File                                               | Role                                                                                  |
|----------------------------------------------------|---------------------------------------------------------------------------------------|
| `pyproject.toml`                                   | Declares the Python version and the pinned FastMCP dependency.                        |
| `07-elicitation/labs/server.py`                    | Creates the `FastMCP` server, registers the tool, and chooses stdio or HTTP.          |
| `07-elicitation/labs/tools/bidirectional_batch.py` | Implements the batch loop, progress reports, question, saved state, and final answer. |
| `07-elicitation/labs/client.py`                    | Connects to the server, shows progress, asks for terminal input, and calls the tool.  |

`mcp.tool(bidirectional_batch)` makes the Python function available as an MCP
tool named `bidirectional_batch`. The function's `initial_batch_size` is a tool
argument. FastMCP supplies `ctx: Context`, which the tool uses to report
progress and inspect the current request; the caller does not type a `ctx`
value.

## One complete example

1. `client.py` calls `bidirectional_batch` with `initial_batch_size=4`.
2. The tool checks for MCP protocol version `2026-07-28`, limits the initial
   size to 1–10, and simulates four rows. `ctx.report_progress(...)` sends an
   update after each row. These updates are **notifications**, not final tool
   results.
3. The tool returns `InputRequiredResult` instead of a final string. Its
   `input_requests["next_batch"]` contains an `elicitation/create` form asking
   for `batch_size`. Its `request_state` stores `total_processed=4` and
   `batch_number=1`.
4. FastMCP invokes the client's `elicitation_handler`. The handler reads a
   number from the terminal and returns an accepted `ElicitResult`. The FastMCP
   client repeats the tool call with that answer and the state token.
5. If the answer is `2`, the tool resumes with the saved count, simulates two
   more rows, and asks again. If the next answer is `0`, it returns
   `Total rows processed: 6`. The original `client.call_tool(...)` then
   completes and prints `[RESULT]`.

The Python client handles the intermediate rounds automatically. From the
application code's point of view, there is one `call_tool` awaiting a final
result. On the protocol, there are multiple `tools/call` requests. This is a *
*multi round-trip request** (MRTR): the server returns a request for input, and
the client retries the original operation with the answer. The `next_batch` key
links the question to the matching response.

## Why keep `request_state`?

Each round enters `bidirectional_batch` from the top. Local variables such as
`total_processed` do not survive the return. The tool therefore serializes the
count and batch number as JSON in `request_state`. On the next round it reads
`ctx.request_state` and the answer in `ctx.input_responses`.

The client carries this state between rounds, but the server owns its meaning.
In the installed FastMCP 4.2.0 implementation, a server boundary seals outgoing
state and verifies it on return; application code sees the decoded JSON string.
A real service with several server instances needs a shared state protection
policy so another instance can verify the token. The lab uses a local,
single-process setup and has no user authentication or persistent jobs.

The client also checks `client.protocol_version` before calling the tool, and
the tool checks the version again in its request context. This matters because
the code explicitly uses the `2026-07-28` input-required result. A peer using an
earlier protocol version cannot run this flow unchanged.

## Progress, elicitation, and transports

**Progress** means “work is still happening.” The tool reports `total_processed`
as its progress value and leaves `total=None`, so it does not promise a known
grand total. The client's `progress_handler` prints only each message.

**Elicitation** means the tool needs information from the user. The server
describes a form with an integer `batch_size` from 0 to 10. The client displays
the question in the terminal and checks the typed value. The server checks the
answer again: a client can send malformed input, and only the server decides
whether to proceed. An accepted `0` finishes; a declined or canceled response
also stops with the count so far.

**Transport** is how client and server exchange MCP messages. In-memory runs
both in one Python process; stdio launches the server as a child process; HTTP
connects to a server already listening at the local URL. The tool's batch logic
is the same in all three modes.

## If something goes wrong

- `Expected 2026-07-28`: check the installed package versions and the server you
  connected to. The client stops before the tool call if its protocol version
  differs.
- `Missing elicitation response` or `Batch size must be between 0 and 10`: the
  server did not receive an accepted, valid answer on a continuation round. The
  terminal handler normally prevents this, but the server validates it too.
- `Connection refused` in HTTP mode: start `server.py --transport http` first
  and check the URL and port. The HTTP server could not bind to port 8000 in the
  environment used to prepare this README, so that run mode was not verified
  here. In-memory and stdio were run successfully.
- The example may not run forever: FastMCP's client limits the number of
  input-required rounds. Enter `0` to finish before that limit.

## References

- [MCP Python SDK: multi round-trip requests](https://py.sdk.modelcontextprotocol.io/handlers/multi-round-trip/)
- [MCP Python SDK: migration to the 2026-07-28 protocol](https://py.sdk.modelcontextprotocol.io/migration/)
- [FastMCP 4 protocol overview](https://blog.gofastmcp.com/3mufbh2vcv22o)
- [MCP 2026-07-28 release overview](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
