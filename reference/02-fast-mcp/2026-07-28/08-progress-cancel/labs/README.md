# MCP cancellation: production action and test timing

Reference for the refactored `verify_progress.py` in this lab.

**Production cancellation does not depend on progress.** A user action invokes
`cancel_call(call)`. The test waits for first progress only to choose a
repeatable
moment to invoke that same function.

This lab expects MCP protocol **`2026-07-28`** and rejects other negotiated
versions. Protocol version and installed SDK version are separate things. The
transport details below assume a compatible SDK; they are not promises about
older installations. Official sources were checked on November 26, 2026.

## 1. The problem this example solves

A user starts `process_records`, then clicks Cancel while it is running.
Cancellation should work before or after the first progress update. Progress is
optional; the user should not have to wait for it to cancel.

An automated test has another requirement: it must demonstrate cancellation
while server work is active. Cancelling immediately after creating the client
task might stop it before it even sends the request. Waiting for progress gives
the test evidence that the server started work.

Keep those two requirements separate:

| Part                                | Responsibility                                                  | Used in production?                                   |
|-------------------------------------|-----------------------------------------------------------------|-------------------------------------------------------|
| `cancel_call(call)`                 | Request cancellation and observe the client task's outcome      | Yes                                                   |
| `example_cancel(...)`               | Arrange a test point, invoke the action, assert the outcome     | Test wrapper                                          |
| `record_first_progress(...)`        | Signal that the test received progress                          | Only for this test, unless the UI also needs progress |
| `first_progress`                    | Client event shared by the test callback and waiter             | Test timing                                           |
| `operation_id`                      | Correlate one request with its own server observations          | Test verification                                     |
| `CallObservation.cancellation_seen` | Per-call event set only when that tool catches `CancelledError` | Test verification                                     |
| `CallObservation.cleanup_finished`  | Per-call event set when that tool reaches `finally`             | Test verification                                     |

See [FastMCP tool calls][tools] and [progress handlers][progress].

## 2. The reusable cancellation action

This is the function in `verify_progress.py`:

```python
async def cancel_call(call: asyncio.Task[Any]) -> bool:
    if call.done():
        print("[CANCEL] Call already finished; observing its outcome",
              flush=True)
    else:
        print("[CANCEL] Cancellation requested; cancelling the call",
              flush=True)
        call.cancel()

    try:
        await call
    except asyncio.CancelledError:
        print("cancellation: client call raised CancelledError", flush=True)
        return True
    else:
        print("cancellation: client call returned normally", flush=True)
        return False
```

`call.cancel()` requests cancellation. Awaiting the task observes how it ends.
There is no progress wait, timeout, or test assertion inside this function.

| Outcome                                  | Function behavior        | Meaning                             |
|------------------------------------------|--------------------------|-------------------------------------|
| Pending task ends cancelled              | Returns `True`           | Client task ended cancelled         |
| Task was already cancelled               | Returns `True`           | Existing cancellation was observed  |
| Task already returned normally           | Returns `False`          | Cancellation arrived too late       |
| Task suppresses cancellation and returns | Returns `False`          | Client task did not end cancelled   |
| Task raises a tool or transport failure  | Propagates the exception | The caller must handle that failure |

`call.done()` alone does not mean success: a completed task may have returned,
failed, or been cancelled. This is why the function still awaits it.

Calling `call.cancel()` does **not** synchronously send a network message. It
requests cancellation of this Python task. When the event loop next runs the
task, the cancellation is delivered at a pause point; the MCP client then has
the opportunity to signal the server for an in-flight request. Calling
`await call` observes the result; it does not initiate the tool call. A call
that was cancelled before sending a request has no server request to cancel.

**`True` does not confirm remote cleanup, undo completed writes, or stop an
independent worker job.** It reports the local task's outcome.

Python documents this cooperative behavior in [task cancellation][asyncio].

## 3. Connecting it to a user action

Start and retain the task inside the application's open client context:

```python
# Within an existing async with Client(...) block:
call = asyncio.create_task(
    client.call_tool(
        "process_records",
        {"count": 20, "delay_seconds": 0.5},
        timeout=300,  # Illustrative application timeout; choose your own.
    )
)
```

There is no `progress_handler` argument. Add one only if you want to display or
record progress. Omitting a per-call handler may still leave a client-level
handler in effect. [FastMCP documents both handler scopes][progress].

Later, inside the UI's existing **async Cancel handler**, on the same event
loop:

```python
was_cancelled = await cancel_call(call)
```

These are two separate moments. Do not run the second block immediately after
creating the task unless immediate cancellation is what you intend.

The application owns the task reference and keeps the client connection open
while the operation is active. Its normal result-handling path must also handle
`CancelledError` if it awaits this task. The UI framework determines how to wire
an async handler; this lab does not include that framework integration.

For a backend serving multiple users, associate each active task with its owning
user and operation. A Cancel endpoint must authenticate the caller and verify
that ownership before looking up the task. This is application design guidance,
not something the local helper implements.

## 4. When the task actually runs

`client.call_tool(...)` creates a coroutine object. `asyncio.create_task(...)`
wraps that coroutine in a task and schedules it on the running client event
loop. It does not need `await asyncio.wait_for(...)` to start.

In an application, the Start handler returns control to the event loop. The
loop can then run the call task. When the task waits for a server response, it
pauses and the loop can handle other work, including a later Cancel click.
The application must keep its event loop running, its client context open, and
a reference to the task. [Python's task documentation][asyncio].

**Yielding** means that the current task pauses so another ready task can run.
An `await` can cause this pause when the awaited operation is still waiting.
An `await` whose result is ready may return immediately without switching tasks.
The client task naturally waits for the server's response; the test's
`await asyncio.wait_for(first_progress.wait(), ...)` is only a way to choose
when the test presses Cancel.

| Client action                                             | Gives the event loop a chance to run other tasks? |
|-----------------------------------------------------------|---------------------------------------------------|
| Return from the Start handler                             | Yes                                               |
| Await a pending server response or an unset event         | Yes                                               |
| `asyncio.create_task(...)` alone                          | Schedules work; the current handler keeps running |
| Call `cleanup_finished.clear()` or `.set()`               | No; these change an event flag                    |
| Run a long synchronous operation on the client event loop | No, until it finishes                             |

If the client event loop is blocked, it cannot run the Cancel handler or send
the cancellation signal yet. If the request was already sent, a server in a
separate process can finish the tool during that time. Once the client unblocks,
the user's cancellation may be too late. Also, `call.done()` can still be
`False` at that point because the blocked client has not processed the server's
response; `False` does not prove that the server is still working. If the loop
blocked before sending the request, the server may never have started it.

The server has its own scheduling. In the attached `process_records` example,
`await asyncio.sleep(delay_seconds)` gives the **server's** event loop an
opportunity to run other work. It does not unblock a blocked client event loop.

## 5. What happens across the transport

For protocol `2026-07-28`:

| Transport                                       | Cancellation signal                                        | Server behavior                                                    |
|-------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------------|
| stdio                                           | `notifications/cancelled` identifying the original request | SDK cancels the associated handler                                 |
| Streamable HTTP with a cancellable SSE response | Close that request's response stream                       | Server detects the closure and cancels its handler                 |
| In-memory                                       | SDK's in-process transport path                            | No separate server process; the lab can also inspect shared events |

The SDK owns request IDs and transport signaling. Application code cancels its
awaiting task; it does not manually construct protocol messages. For an active
request, the compatible Python SDK performs transport signaling when it handles
the task cancellation. Its [migration guide][migration] describes cancellation
of the task awaiting a request and warns that v1 did not propagate it to the
server. A local `CancelledError` is not proof that the server received the
signal or finished cleanup.

The modern Python HTTP transport translates its internal cancellation frame into
stream closure and does not POST that notification. Earlier HTTP protocol
versions use different behavior. See the [Python transport implementation][http]
and the [official protocol-version comparison][versions].

For a cancelled request under this protocol, the server must not send further
messages for that request, including a normal result or cancellation error. The
client stops waiting; it does not wait for a final cancellation acknowledgment.
See the [Python SDK migration guide][migration].

**HTTP configuration matters.** The Python SDK documents that modern
`json_response=True` disables propagation to the handler. It also documents a
separate cancellation limitation for legacy `stateless_http=True`. Confirm your
server's actual response mode and SDK behavior when testing
HTTP. [Source][server-cancel].

## 6. One concrete request journey

Illustrative request ID: `17`. The actual SDK chooses it.

1. The Start handler creates and stores the task, then returns to the client
   event loop.
2. The event loop runs the call task; the SDK sends `process_records` as
   request `17` and waits for a response.
3. The server starts processing. It may send progress, but cancellation does not
   depend on receiving any.
4. The user clicks Cancel. The application finds this user's task and invokes
   `cancel_call(call)`.
5. `call.cancel()` requests task cancellation. When the client event loop runs
   the task, the SDK maps it to request `17`: a stdio notification or modern
   HTTP stream closure.
6. The server handler receives cancellation at a cooperative checkpoint. Its
   `except asyncio.CancelledError` block sets this operation's
   `cancellation_seen` and re-raises; its `finally` block sets this operation's
   `cleanup_finished`.
7. The client helper observes `CancelledError` and returns `True`.

Steps 6 and 7 do not establish an acknowledgment sequence. Client cancellation
may be observed before server cleanup finishes.

The MCP request ID identifies which request to cancel. A progress value such as
`1` identifies work completed; it is not the cancellation identifier.

## 7. What the test wrapper adds

`example_cancel(...)` performs these steps:

1. Generate a unique `operation_id` and create the client-local
   `first_progress` event. For in-memory mode, reserve this operation's own
   `CallObservation` before sending the request.
2. Start a tool call with that ID and `record_first_progress` as its callback.
3. Wait up to `WAIT_SECONDS` for that callback to set the event.
4. Check that the call has not already finished.
5. Invoke the production action: `await cancel_call(call)`.
6. Assert that the action returned `True`.
7. In in-memory mode, wait for **this operation's** `cancellation_seen` to
   confirm the server caught `CancelledError`, then its `cleanup_finished` to
   confirm it reached `finally`.

The tool delay gives the test time to react. First progress is an observable
milestone, not an exact scheduling guarantee. If the call already finished, the
test surfaces its failure or reports that it missed the cancellation window.

Production should handle an already finished call normally. The test raises an
assertion because it failed to exercise the behavior it was meant to verify.

| Timing mechanism                                      | Role in this lab                            |
|-------------------------------------------------------|---------------------------------------------|
| `wait_for(first_progress.wait(), ...)`                | Bound the test's wait for its trigger       |
| `client.call_tool(..., timeout=15)`                   | Bound the tool call's duration              |
| `wait_for(observation.cancellation_seen.wait(), ...)` | Bound this call's server cancellation check |
| `wait_for(observation.cleanup_finished.wait(), ...)`  | Bound this call's cleanup check             |

The first timeout cancels the event waiter, not the tool call. The wrapper's
`finally` explicitly cancels and awaits unfinished tool work. These test bounds
are independent of user-requested cancellation.

## 8. Understanding the server verification signals

These signals have different owners:

| Event                           | Owner            | Purpose                                                |
|---------------------------------|------------------|--------------------------------------------------------|
| `first_progress`                | Client test      | Trigger cancellation after observed server activity    |
| `observation.cancellation_seen` | Server tool call | Prove this call caught `CancelledError`                |
| `observation.cleanup_finished`  | Server tool call | Prove this call reached `finally`, whatever the reason |

Each `process_records` call has a unique `operation_id` and a new
`CallObservation` containing two initially unset events. The tool's
`except asyncio.CancelledError` sets its `cancellation_seen`, then re-raises.
Its `finally` sets its `cleanup_finished` and removes its ID from the registry.
The test holds a direct reference to its own observation, so it can still read
both events after the registry removes the entry. `await event.wait()` pauses
until that event is set. See [Python's event docs][event] and [task cancellation
guidance][asyncio].

The distinction matters: a normal completion also runs `finally` and sets its
`cleanup_finished`, but it never sets its `cancellation_seen`. Therefore the
in-memory test checks the server's actual cancellation path rather than
inferring it from the client task's `CancelledError` or from `finally` alone.
The example has no real resources to release; `cleanup_finished` records only
that it reached `finally`. Separate fresh events avoid a previous call's signal
and avoid one call clearing another call's signal.

Two calls can run at once: the server records their events under different IDs,
and each test waits only on the observation matching the ID it sent. Duplicate
active IDs are rejected. The ID here is a test correlation value; it is not an
MCP request ID or an authorization credential. Production applications must
verify user ownership before allowing a user to cancel another user's task.

In-memory mode can share the same event objects. A subprocess or external HTTP
server has its own memory; importing the same module name into the client does
not share events across processes. The wrapper therefore skips those assertions
for stdio and HTTP. The server writes `[CANCELLED]` when it catches the
exception
and `[CLEANUP]` when it reaches `finally`; inspecting stderr is useful but is
not an automated cross-process assertion.

`CallObservation` is created **on the server for every transport**, but its
usefulness depends on who can read it:

| Transport | What `CallObservation` contributes                                                                                                            |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| In-memory | Client test and server share the same per-call events, so the test can wait for this call's cancellation and `finally` signals.               |
| stdio     | The server sets the events, then removes the observation. The client cannot see them; the operation ID in stderr is the available diagnostic. |
| HTTP      | Same server-local events and diagnostic logs; another process or worker cannot read this observation object.                                  |

For stdio and HTTP, the present `CallObservation` does **not** give the client
an acknowledgment. Its event fields are test instrumentation for in-memory
mode. If a cross-process status store is introduced, that store would become
the test's readable evidence; retaining these server-local events would be
optional. This does not change the MCP request's cancellation path.

The in-memory observation registry is local to one Python process. StdIO and
HTTP use IDs in server stderr but cannot check those events directly from the
client. The cancellation event records that a tool caught cancellation; it
does not distinguish a user click from a timeout. Neither event proves that
external side effects were reversed.

## 9. Verifying cancellation across processes (design only)

The current code logs server events for stdio and HTTP, but does **not**
automatically assert them. A cancelled request cannot return a final
acknowledgment under protocol `2026-07-28`; the server must not send more
messages for that request. Verification must use another observation channel.
See the [Python SDK cancellation migration notes][migration].

| Option                         | How the test observes the server                                                              | When to choose it                                                                |
|--------------------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| Capture stderr or server logs  | Match `[CANCELLED]` and `[CLEANUP]` lines by `operation_id`                                   | A controlled lab where the test harness captures the server process and its logs |
| Store status by `operation_id` | Read `started`, `cancellation_seen`, and `cleanup_finished` through a separate store or query | Automated checks across processes, hosts, or HTTP workers                        |

For this lab, capturing server logs is the simpler next step if the test
harness can capture them reliably. StdIO protocol output belongs on stdout;
diagnostic lines stay on stderr. The harness must consume stderr while the
process runs and select lines matching **this call's** operation ID. For HTTP,
the harness needs access to the server logs, not just the client's output.
Logs from different requests may arrive interleaved.

When log capture is unavailable or a durable assertion is required, use a
status store visible to the server and the test. A local database can serve
separate local processes; a remote server or multiple HTTP workers need a store
they all share. A server-only dictionary is insufficient if the test cannot
read it, the process exits, or a later query lands on another worker. Keep the
status long enough for the test to query it, then expire or remove it.

One concrete flow, with a **synthetic** operation ID `A`:

1. The client includes `operation_id=A` in `process_records` and retains the
   task for that call. The server records `A: started` in the shared store.
2. The test reaches its chosen trigger and cancels that client task.
3. If the server tool catches `CancelledError`, the server records
   `A: cancellation_seen`; when it reaches `finally`, it records
   `A: cleanup_finished`. A normal finish records cleanup without the
   cancellation marker.
4. After observing the client task's outcome, the test reads status for `A`
   through a **separate** query. It waits up to a fixed limit for both server
   markers. It never waits for a response on the cancelled request.

The application owns the client task; the server owns the status record.
`operation_id` is a correlation value, **not** a secret or an authorization
check. A user-facing status query must authenticate the caller and verify
ownership of `A`. A trusted test harness may read its test store directly.
If writing status requires an `await` during server cleanup, that write needs
bounded protection from the cancellation scope; see [server cleanup
guidance][server-cancel].

If the client observes `CancelledError` but `A: cancellation_seen` never
appears,
the test reports **server cancellation unconfirmed** after its timeout. Check
that the request started, the transport and SDK propagated cancellation, and
that the status channel itself worked. Do not treat the client exception or
another operation's marker as proof. This status design belongs to a future
cross-process test; it has not been added to this code.

## 10. Server cooperation and cleanup

Server code needs cancellation checkpoints and a `finally` cleanup path. Avoid
swallowing the cancellation exception. Blocking work can delay cancellation;
request cancellation is not a forceful process kill.

In an AnyIO cancellation scope, cleanup that awaits may need a shield and a time
limit. The Python SDK also documents explicit cooperative checks for synchronous
handlers running in worker threads. Apply those rules to your actual framework
and execution path. [Official server cancellation guidance][server-cancel].

This README does not change the server tool or its cleanup implementation.

## 11. A realistic failure and recovery

**Scenario:** the client shows cancellation, but the HTTP server continues
processing records.

First check whether the server receives the cancellation signal. Confirm the
negotiated protocol, HTTP response mode, and SDK versions. Then inspect whether
the handler is blocked or suppresses cancellation. Compare with the in-memory
example to distinguish a tool cleanup issue from transport propagation.

If records were already written, cancellation alone does not undo them. Before
retrying, inspect the operation's recorded state. Use your application's
idempotency or resume rules to avoid processing those records twice.

For work deliberately handed to an independent worker, cancel the worker job
through its own authorized lifecycle. A client task is a handle to the MCP call;
it is not automatically a handle to every job that call may have started.

| Requirement                                                         | Suitable approach                                                      |
|---------------------------------------------------------------------|------------------------------------------------------------------------|
| Stop one active MCP request                                         | Cancel its awaiting task                                               |
| Show live work completed                                            | Add an optional progress handler                                       |
| Keep a job alive after the caller disconnects, then cancel it later | Use an explicit job ID, stored status, and authorized job cancellation |

The first option is the simplest fit for this lab. The last requirement changes
the design because the job must have a lifetime independent of this call.

## 12. Running the existing examples

Place this README beside `verify_progress.py` in the existing lab. The script
also needs `server.py`, `tools/process_records.py`, and the lab's compatible
dependencies. They are not included in this README.

From that directory:

```bash
python verify_progress.py --transport in-memory --example progress
python verify_progress.py --transport in-memory --example cancel
python verify_progress.py --transport in-memory --example cancel --concurrent 2
python verify_progress.py --transport stdio --example cancel
```

For HTTP, start the lab's server using its existing HTTP startup command. The
client expects `http://127.0.0.1:8000/mcp`. Then run:

```bash
python verify_progress.py --transport http --example cancel
```

The script launches the stdio server itself. The HTTP server must already be
running. Server diagnostic output should use stderr when stdout carries stdio
protocol messages.

The cancellation example verifies the first-progress test case. With
`--concurrent 2`, two tool calls overlap and each checks its own server
cancellation and `finally` markers. It does not exercise every possible
cancellation moment. The
`server.py` integration and compatible dependencies are needed for full MCP
transport runs.

## Official references

- [Python asyncio task cancellation][asyncio]
- [Python asyncio event flags][event]
- [FastMCP tool calls and execution options][tools]
- [FastMCP progress handlers][progress]
- [MCP Python SDK server cancellation][server-cancel]
- [MCP Python SDK migration and cancellation propagation][migration]
- [MCP Python SDK Streamable HTTP implementation][http]
- [MCP SDK protocol `2026-07-28` transport comparison][versions]

[asyncio]: https://docs.python.org/3.12/library/asyncio-task.html#task-cancellation

[event]: https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Event

[tools]: https://gofastmcp.com/docs/clients/tools

[progress]: https://gofastmcp.com/docs/clients/progress

[server-cancel]: https://py.sdk.modelcontextprotocol.io/handlers/cancellation/

[migration]: https://py.sdk.modelcontextprotocol.io/migration/

[http]: https://py.sdk.modelcontextprotocol.io/api/mcp/client/streamable_http/

[versions]: https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28
