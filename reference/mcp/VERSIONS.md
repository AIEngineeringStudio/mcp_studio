# Version baseline and compatibility

Checked 2026-11-15. Protocol revision, framework release, runtime version,
and host support are separate compatibility dimensions.

## Protocol baseline

The explanations target **MCP 2026-07-28**. The official
[versioning reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
distinguishes modern self-contained requests from legacy initialization-based
versions through 2025-11-25.

Modern requests declare version and client capabilities in metadata.
Server discovery is available without a mandatory initialization handshake.
The [HTTP binding](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
defines corresponding headers and request-scoped response streams.
Modern HTTP removes protocol sessions, the GET stream, and event-ID
resumability. Application state and idempotency remain separate concerns.

The [MRTR reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
defines input-required results, new request IDs on retry, input responses,
and opaque continuation state. Do not blend it with legacy suspended-handler
diagrams as if they described the same wire sequence.

## Implementation baseline

The lab pins standalone **FastMCP 4.2.0**, the stable release shown on the
[official release page](https://github.com/PrefectHQ/fastmcp/releases/tag/v4.2.0)
when checked. The lockfile resolves **mcp 2.3.0**. The lab imports `FastMCP`
from `fastmcp`, not from `mcp.server.fastmcp`.

The [Python SDK migration guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md)
describes SDK v1-to-v2 changes, including its high-level `MCPServer` name.
Do not assume those changes apply identically to standalone FastMCP.

FastMCP's documentation follows its main branch and can describe unreleased
features. Prefer the pinned package's behavior when implementing examples.
Tests establish only the exercised features.

## Python and platforms

The current stable Python release found was
[Python 3.15.2](https://www.python.org/downloads/release/python-3152/).
The isolated concept lab was executed on **CPython 3.14.3 on Intel macOS**,
using an interpreter available through the installed tooling. An attempted
3.14.10 download was unavailable in those interpreter catalogs, including
a workspace-local trial of uv 0.12.1.

The `.python-version` records the **tested concept snapshot**, not a production
runtime recommendation. It is an older patch release. The example contains
synthetic data, no credentials, and a loopback-only HTTP listener. Before a
production extension, select a current supported patched runtime and rerun
the checks. Do not call a version LTS without an upstream support statement.

Source and commands are architecture-neutral. Apple Silicon was not executed.
Compatible native dependencies must be verified on that Mac; a lockfile is
not proof of execution on every platform.

## Advanced compatibility

Roots, sampling, and protocol logging are deprecated in the modern revision.
Apps, Tasks, and Skills are optional extensions. Check both endpoints and the
host experience before relying on them. The
[extension index](https://modelcontextprotocol.io/extensions/overview) describes
their separate lifecycle; older task examples may use different methods.

## Updating this baseline

Check versioned official specifications and package releases; identify changed
flows; update affected guides; pin the implementation; refresh the lockfile;
run relevant examples; record actual runtime, platform, and scope in
[VALIDATION.md](VALIDATION.md). Preserve the historical references.
