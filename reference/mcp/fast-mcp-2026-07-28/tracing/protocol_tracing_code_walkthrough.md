# Understanding `protocol_trace.py` — Beginner walkthrough

Lets walkthrough the `protocol_trace.py` file, using one example:

```
await client.call_tool("get_ticket", {"ticket_id": "T-100"})
```

The goal is to understand **how we can observe JSON-RPC messages without
changing how the client and server communicate**.

## 1. The big idea: Wrap a stream

Imagine a stream as a pipe that carries messages.

Without tracing:

```
CLIENT                         SERVER
+------------+               +------------+
| MCP Client |               | MCP Server |
+-----+------+               +------+-----+
      |                             ^
      |       JSON-RPC message      |
      +---------------------------->+
```

With tracing:

```
CLIENT                              SERVER
+------------+                   +------------+
| MCP Client |                   | MCP Server |
+-----+------+                   +------+-----+
      |                                 ^
      v                                 |
+------------+                   +------------+
| Trace OUT  |                   | Trace IN   |
| Log message|                   | Log message|
| Forward it |                   | Forward it |
+-----+------+                   +------+-----+
      |                                 ^
      +---------------------------------+
                   STDIO
```

The trace objects sit between the MCP session and the real stream.

They perform two actions:

1. Log the message.
2. Pass the **same message object** to the original stream or caller.

They do not create JSON-RPC requests, execute tools, or modify responses.

This pattern is called a *wrapper*, and more specifically a *decorator*.

## 2. Understand the five main parts

1. `_log()` — formats and prints a message

2. `TraceReceiveStream` — intercepts incoming messages

3. `TraceSendStream` — intercepts outgoing messages

4. `TracedStdioTransport` — installs the wrappers on the client

5. `install_server_stdio_trace()` — installs them on the server

### Part 1 — `_log()` (lines 27–42)

This is the simplest function.

```
def _log(side, direction, item):
```

It receives three values:

| Parameter   | Example          | Meaning                              |
|-------------|------------------|--------------------------------------|
| `side`      | `"CLIENT"`       | Which process is logging?            |
| `direction` | `"OUT"`          | Is the message outgoing or incoming? |
| `item`      | `SessionMessage` | What message was observed?           |

Inside it, this statement is important:

```
envelope = item.message.model_dump_json(by_alias=True, exclude_unset=True)
```

A `SessionMessage` contains a parsed JSON-RPC message object.

`model_dump_json()` converts that object into a JSON string suitable for
logging.

- `by_alias=True` uses field aliases defined by the model.
- `exclude_unset=True` omits fields that were not explicitly set.

For example, the logged JSON might be:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/list"
}
```

This is a reconstruction of the parsed JSON-RPC message, **not a capture of the
original STDIO bytes**.

Finally:

```
print(
    f"{timestamp} [{side} {direction}] {envelope}",
    file=sys.stderr,
    flush=True
)
```

Why `stderr`?

Because STDIO MCP uses `stdout` for protocol messages. Printing debug messages
there would interfere with communication. The MCP Python SDK documents this
separation.

The surrounding `try/except` prevents a logging error from interrupting MCP
execution. One tradeoff is that logger failures can be hidden.

### Part 2 — `TraceReceiveStream` (lines 45–58)

This is our incoming-message observer.

```
async def receive(self):
    item = await self._inner.receive()
    _log(self._side, "IN", item)
    return item
```

Read it one line at a time.

**Line 1:**

```
item = await self._inner.receive()
```

`self._inner` is the original receive stream provided by the MCP SDK.

We wait until it produces a message.

**Line 2:**

```
_log(self._side, "IN", item)
```

Record the incoming message.

**Line 3:**

```
return item
```

Pass the same object to the MCP session.

The critical idea:

```
Original receive stream
          |
          v
       receive()
          |
          v
       log(item)
          |
          v
      return item
          |
          v
       MCP Session
```

Why is `return item` necessary?

Without it, the session would not receive the message. The tool call could
remain blocked or fail.

The `aclose()` method simply closes the wrapped stream when it is no longer
needed.

### Part 3 — `TraceSendStream`(lines 61–73)

This is almost the opposite of `TraceReceiveStream`.

```
async def send(self, item):
    _log(self._side, "OUT", item)
    await self._inner.send(item)
```

The sequence is:

```
       MCP Session
            |
            v
         send(item)
            |
            v
         log(item)
            |
            v
     Original send stream
            |
            v
        STDIO transport
```

Notice the difference.

**Receive:** Read first, then log.

**Send:** Log first, then send.

This means `[CLIENT OUT]` proves that the session *attempted* to send a message.
It does not prove the server received it.

If the underlying send fails, the trace can still contain `[CLIENT OUT]`.

This distinction becomes important when diagnosing failures.

Both wrapper classes use AnyIO's object-stream interfaces, which define
asynchronous `send()`, `receive()`, and stream-lifecycle behavior.

## 3. Who installs these wrappers?

The previous two classes do the actual message observation. The next two parts
connect them to FastMCP.

### Part 4 — `TracedStdioTransport`(lines 76–102)

This class is used by your client.

The most important statement is:

```
async with stdio_client(params) as (read_stream, write_stream):
```

The MCP SDK opens a subprocess running your server and provides two streams.

Then:

```
async with options.session_class(
    TraceReceiveStream(read_stream, "CLIENT"),
    TraceSendStream(write_stream, "CLIENT"),
    **session_kwargs,
) as session:
    yield session
```

Let's understand the sequence.

```
TracedStdioTransport.connect_session()
                 |
                 v
       Start server subprocess
                 |
                 v
       SDK creates two streams
                 |
          +------+------+
          |             |
          v             v
     Read stream    Write stream
          |             |
          v             v
     TraceReceive   TraceSend
          |             |
          +------+------+
                 |
                 v
         Create MCP session
                 |
                 v
          yield session
```

`yield session` gives FastMCP access to the session so normal operations can
continue.

`@asynccontextmanager` makes this possible while also ensuring that, when the
connection ends, Python exits the nested context managers and performs their
cleanup.

This class still uses the SDK's original `stdio_client`. We are only inserting
observers around its streams.

### Part 5 — `install_server_stdio_trace()`(lines 105–127)

The server needs the same wrappers, but the server creates its STDIO connection
differently.

This function locates FastMCP's STDIO runner:

```
runner = importlib.import_module(
    "fastmcp.server.mixins.transport"
)
```

It then saves the original `stdio_server` and substitutes a wrapper that calls
that original function.

Inside the wrapper:

```
yield (
    TraceReceiveStream(read_stream, "SERVER"),
    TraceSendStream(write_stream, "SERVER"),
)
```

This gives the server session the same tracing behavior as the client.

The `_protocol_trace_installed` flag prevents wrapping the runner repeatedly if
the installer is called again.

**Important limitation:** This is a *monkey patch*. It replaces a reference
inside FastMCP at runtime. The import path and function structure can change
between releases, so this integration is version-sensitive.

For a learning project, it is reasonable. For production, I would prefer a
supported tracing extension point if one provides the required envelope
visibility.

## 4. Follow one complete request

Now combine everything.

Your application calls:

```
await client.call_tool("get_ticket", {"ticket_id": "T-100"})
```

Here is the complete path:

```
CLIENT PROCESS                     SERVER PROCESS

FastMCP client.call_tool()
         |
         v
MCP session creates request
         |
         v
TraceSendStream.send()
         |
         +-- [CLIENT OUT]
         |
         v
Original STDIO send stream
         |
         | JSON-RPC via stdin
         |
         v
                                 Original receive stream
                                           |
                                           v
                                 TraceReceiveStream.receive()
                                           |
                                           +-- [SERVER IN]
                                           |
                                           v
                                 MCP server handles request
                                           |
                                           v
                                 get_ticket("T-100")
                                           |
                                           v
                                 MCP server creates response
                                           |
                                           v
                                 TraceSendStream.send()
                                           |
                                           +-- [SERVER OUT]
                                           |
                                           v
                                 Original STDIO send stream
                                           |
         +---------------------------------+
         |
         v
Original receive stream
         |
         v
TraceReceiveStream.receive()
         |
         +-- [CLIENT IN]
         |
         v
FastMCP client receives result
```

This is why **the same two wrapper classes work on both sides**. The difference
is only the value passed as `side`: `"CLIENT"` or `"SERVER"`.

## 5. Why not just use `print()` inside `get_ticket()`?

There are three alternatives:

| Approach                             | Benefit                                                         | Problem                                   |
|--------------------------------------|-----------------------------------------------------------------|-------------------------------------------|
| `print()` inside tools               | Very simple                                                     | Cannot see protocol requests or discovery |
| FastMCP semantic middleware          | Covers higher-level operations                                  | Does not show complete JSON-RPC envelopes |
| Stream wrappers (our implementation) | Shows request IDs, JSON-RPC methods, results, and notifications | Depends on the SDK's stream interfaces    |

For your current goal, the stream wrapper is the right choice for STDIO.

It observes messages without needing changes to `get_ticket()`,
`ticket_resource()`, or `summarize_ticket()`.

## 6. Verify what you understood

Run:

```shell
python verify_primitives.py --transport stdio --focus tools 2>trace.log
```

Look for the same request ID in these four observations:

```
[CLIENT OUT] id=7
[SERVER IN]  id=7
[SERVER OUT] id=7
[CLIENT IN]  id=7
```

Illustrative request ID. Actual IDs depend on your session.

If `[CLIENT OUT]` exists but `[SERVER IN]` is missing, investigate the
underlying send stream, subprocess, and server connection. The logger is not
proof of successful delivery.

If you get the expected four observations, the stream observers are capturing
both sides of the exchange.

## Key takeaway

You only need to remember three concepts:

- **Stream:** The path through which message objects move.
- **Wrapper:** An object that intercepts stream operations, logs them, and
  forwards the original messages.
- **Transport integration:** The place where we replace the original streams
  with wrapped ones.

The central design is:

```
Original stream
      |
      v
Trace wrapper
      |
      +----> Logging
      |
      v
Original message continues
```

**The most important code to understand first is&#x20;**
`TraceReceiveStream.receive()`**&#x20;and&#x20;**`TraceSendStream.send()`**.**
Everything else in `protocol_trace.py` exists mainly to install those two
wrappers in the correct place.