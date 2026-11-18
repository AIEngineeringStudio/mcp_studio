# Validation record

Examples executed: 2026-11-15 and 2026-11-18. Final library check: 2026-11-16.
Scope: newly authored course and synthetic examples.

## Executed examples

Runtime: CPython 3.14.3, FastMCP 4.2.0, MCP SDK 2.3.0, Intel macOS.
Dependencies resolved in the isolated lab project and are recorded in
`labs/uv.lock`. Caches and downloaded runtime remain within the lab folder.

- Domain tests: **3 passed** (lookup, missing ID, mutation isolation).
- Negative MCP contract tests: **2 passed** (missing argument, unknown record).
- In-memory client: tool discovery/call, resource read, prompt retrieval passed.
- stdio client: the same contracts passed across a real subprocess.
- HTTP client: the same contracts passed through a temporary loopback server.
  The verification helper terminated the process it started.
- Continuation model: decline, cross-user rejection, and sequential replay
  checks passed. This is a domain simulation, not an MCP MRTR implementation.
- Calendar authorization: the MCP SDK served Protected Resource Metadata and a
  `401` discovery challenge; read and write tokens received different private
  tool catalogs; Bob could read only Bob's synthetic calendar; a direct
  hidden-tool call was denied; an authorized write used a mock downstream
  credential distinct from the inbound MCP bearer token.
  This is a local concept simulation, not a live provider OBO or calendar call.

The first HTTP attempt was prevented from binding by the execution environment.
The permitted localhost check then passed. Initial dependency access also
required network permission. No external business service or model was called.

Memory, stdio, and HTTP checks explicitly asserted modern protocol `2026-07-28`.

## Scope of review

All original files were inventoried with content hashes. Source review combined
full-text structural/overlap analysis, thematic inspection, and selected close
reading. The catalog records exact duplicates and specific correctness risks.
This is not a line-by-line audit of every archived example.

The 32 guides have explicit outcomes, prerequisite navigation, source links,
worked examples/failure analysis, and professional wording. Their production
chapters describe designs; no production deployment was implemented.

Library validation passed: all **112 source hashes match the snapshot**, **32 guide
entries**, **40 Markdown documents with valid local navigation**, valid JSON
examples, an ordered prerequisite graph, Python syntax checks, and the new
skill's metadata/routing. The generated inventory records **121 similarity
candidates**, which are review hints rather than deletion decisions.

The final catalog refresh follows four `[DONE]` source renames and edits to
the first chunk and `mcp-learning-docs`. The course links and source mappings
use those current paths. This organization pass did not modify source content.

## Limits

Apple Silicon execution, live OAuth, production persistence, Docker deployment,
proxy/TLS behavior, UI rendering, load testing, and real-host extension support
were not executed. Original scripts and images are not runtime/visual certified.
The tested Python patch is an older concept snapshot; see
[VERSIONS.md](VERSIONS.md) before a production extension.

## Repeatable checks

From the workspace root, run the collection validator:

```bash
python3 reference/mcp/catalog/validate_library.py
```

It verifies source hashes, local navigation, guide prerequisites, required skill
metadata, and code syntax. The [lab instructions](labs/README.md) provide the
commands for the executable checks.
