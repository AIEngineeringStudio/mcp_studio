# stdio and subprocess boundaries

**Outcome:** Run the same service in a child process and explain stdin, stdout, and stderr.

**Prerequisites:** [07: The first client and in-memory testing](07-in-memory-client.md).

## One new boundary

The in-memory client imports the server object. The stdio client launches
another Python process and communicates through its standard input and output.

```
Client process                     Server process
write ---------------------------> stdin
read  <--------------------------- stdout
diagnostics <--------------------- stderr
```

Standard streams are operating-system channels. No HTTP port is needed.
The client typically owns the child process lifetime.

## Run and inspect

After [lab setup](../labs/README.md), run:

```bash
uv run python client.py stdio
```

Expected final output:

```
stdio: tool, resource, and prompt checks passed
```

In [client.py](../labs/client.py), `StdioTransport` launches
`sys.executable` with an absolute path to `server.py`. The executable is the
same interpreter running the client, which reduces dependency mismatches.
Resolving the server relative to the client file avoids reliance on the
terminal's current directory.

## Protect the protocol channel

The server must keep stdout for protocol messages. A debug
`print("starting")` to stdout can break parsing before a single tool runs.
Use stderr for diagnostics. The test client's own terminal output is separate
from the child server's protocol stdout.

Messages use newline-delimited JSON-RPC framing. An escaped newline inside a
JSON string is different from inserting a physical newline that splits a
message. Let the transport implementation handle serialization and framing.

## Startup failure versus tool failure

A missing script path or missing package can cause the child to exit before
the protocol is usable. Inspect exit status and stderr first. An unknown
ticket reported after discovery is an application failure and belongs to a
different investigation.

Do not fix a dependency mismatch by blindly switching to a globally installed
Python. Use the pinned project environment and explicit launch configuration.

## Configuration and lifetime

A child process needs an intentionally selected environment. Production host
configuration should avoid leaking unrelated credentials. An application
still needs file-access restrictions and service authorization even though
it does not expose a public HTTP endpoint.

When the client closes its streams, the child should exit or be terminated
under the client's cleanup policy. A server that remains running unexpectedly
may indicate a lifecycle bug.

Stdio is suitable for local production integrations. HTTP becomes useful
when the server must live independently or serve remote clients; “production”
alone does not decide the transport.

**Professional articulation:**

> “Stdio adds an operating-system process boundary while preserving the same
> MCP component contracts. We keep diagnostic output outside the protocol
> stream.”

## Sources and next step

- [Archive: conversations/chatgpt/2_Real_stdio_Subprocess.md](../../conversations/chatgpt/2_Real_stdio_Subprocess.md)
- [Archive: _learning_resources/troubleshoot.md](../../_learning_resources/troubleshoot.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio) — checked 2026-11-15.

Next: [Resources, URIs, and templates](09-resources.md).

