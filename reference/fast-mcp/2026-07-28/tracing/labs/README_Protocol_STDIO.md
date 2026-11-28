# FastMCP 4.2 STDIO protocol tracing lesson

Files: `protocol_trace.py` adds read/write stream observers; `server.py` and
`verify_primitives.py` are copies of the original upload with STDIO tracing
hooked in.

## Run

Install FastMCP 4.2 in your Python environment, then from this directory:

```bash
python verify_primitives.py --transport stdio --focus tools 2>trace.log
python verify_primitives.py --transport stdio --focus resources 2>trace-resources.log
python verify_primitives.py --transport stdio --focus prompts 2>trace-prompts.log
```

The trace log will contain all JSON-RPC requests and responses and any
notifications observed by the wrapped STDIO message streams. Each record
includes side (`CLIENT` or `SERVER`), direction (`IN` or `OUT`), timestamp, and
the complete serialized JSON-RPC envelope (including `id`). `CLIENT OUT` records
an **attempt** to send, not confirmed delivery.

The implementation calls the existing MCP SDK's `stdio_client` and FastMCP's
original `stdio_server` and wraps their `SessionMessage` streams. It does not
write trace output to STDIO protocol stdout. The server integration patches
FastMCP's imported `stdio_server` reference, so check this integration when
upgrading FastMCP.

## Incorporating into your existing semantic-tracing project

If you have already changed your own server and client with semantic logging, do
not replace your files wholesale. Copy `protocol_trace.py`, then:

1. `server.py`: import `install_server_stdio_trace` from `protocol_trace`, and
   call it immediately before `mcp.run(transport='stdio')` (not on the HTTP
   path).
2. `verify_primitives.py`: import `TracedStdioTransport` from `protocol_trace`,
   and use it in `client_source('stdio')` in place of `StdioTransport` with the
   same command/args.
3. Leave semantic tracing already added to your files in place.

**Security:** This educational logger records entire JSON-RPC messages,
including any credentials or sensitive tool arguments. Run it only against the
synthetic local ticket service, or add redaction before using real data.

**Scope:** In-memory and HTTP modes still work as before but do not have
protocol-stream tracing. The protocol observer is not a raw byte-level transport
capture.

**Validation:** Source code is Python syntax checked. An end-to-end FastMCP run
must be completed locally because FastMCP and the MCP SDK are unavailable in the
artifact build environment.
