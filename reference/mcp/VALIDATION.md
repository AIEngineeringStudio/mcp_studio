# Validation record

Examples executed: 2026-11-15 and 2026-11-18. Beginner-documentation check:
2026-11-18. Scope: curated course and synthetic examples.

## Beginner-documentation revision

The entry path and concepts 01 through 06 were revised to introduce ordinary
Python behavior before MCP terminology. The revision defines each foundational
term before use, separates protocol and transport layers, and follows concepts
with small code or message examples. Focused examples were also added to later
abstract chapters.

A follow-up review incorporated the clearer definitions, distinctions, response
outcomes, state boundaries, and failure explanations from elicitation chunks
1–5 into concepts 11–14. Initialization, protocol sessions, GET streams,
resumability, `elicitation/create`, and SDK v1 code remain explicitly confined
to the legacy `2025-11-25` path.

Validation on 2026-11-18 established:

- all concept files have a level-one document title;
- local Markdown links in the course index and concept guides resolve in the
  reorganized source tree;
- `git diff --check` reports no whitespace errors;
- three domain tests and two protocol-contract tests pass;
- in-memory and stdio client checks pass;
- the continuation-state simulation passes.

The documentation examples in production chapters remain labeled conceptual
unless an executed lab or validation entry says otherwise.

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

The course contains 32 numbered concepts plus the beginner orientation and
supplemental lifecycle/primitive comparisons. Source links now use the current
`reference/mcp` folder organization. The archived sources themselves remain
historical material and were not rewritten by the beginner-documentation pass.

## Limits

Apple Silicon execution, live OAuth, production persistence, Docker deployment,
proxy/TLS behavior, UI rendering, load testing, and real-host extension support
were not executed. Original scripts and images are not runtime/visual certified.
The tested Python patch is an older concept snapshot; see
[VERSIONS.md](VERSIONS.md) before a production extension.

## Repeatable checks

The [lab instructions](labs/README.md) provide the commands for executable
checks. Run `git diff --check` from the workspace root for whitespace errors,
and verify local links whenever source folders are reorganized.
