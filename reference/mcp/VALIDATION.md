# Validation record

Examples executed: 2026-11-15, 2026-11-18, and 2026-11-19.
Beginner-documentation check: 2026-11-18. Focused lesson-checkpoint audit:
2026-11-19. Scope: curated course and synthetic examples.

## FastMCP 2026-07-28 lesson-checkpoint audit

All 17 lessons in `fast-mcp-2026-07-28/` were checked on 2026-11-19. Each now
contains one concept-matched `Hands-on checkpoint`, an appropriate code or wire
example, exact setup and run commands, expected output, and a link to complete
runnable source when the inline excerpt is intentionally focused.

The full checkpoint suite passed with CPython 3.14.3, FastMCP 4.2.0, and MCP
SDK 2.3.0 on Intel macOS. The executed checks covered:

- modern `server/discover` and per-request client capability metadata;
- focused tool, resource-template/read, and prompt-rendering calls;
- explicit project scope as a modern roots replacement;
- a deterministic server-owned provider as the sampling replacement;
- continuation decline, identity isolation, and sequential replay safety;
- real FastMCP progress notifications and cooperative cancellation cleanup;
- stderr diagnostics kept separate from stdio protocol traffic;
- opaque application cursors and real `completion/complete` dispatch;
- application lifespan startup/use/shutdown and internal dependency ownership;
- middleware before/handler/after ordering with an unchanged tool schema;
- mounted-server namespacing through ordinary `tools/list` and `tools/call`;
- modern discovery versus legacy initialization against one FastMCP server;
- memory, stdio, and loopback HTTP component calls;
- synthetic OAuth metadata, scoped visibility, direct-call denial, caller
  isolation, and mock downstream credential exchange;
- Host and Origin allowlists: allowed requests returned 200, an invalid Host
  returned 421, and an invalid Origin returned 403.

The five existing unit tests also passed: three domain tests and two negative
MCP contract tests. `git diff --check` and local-link validation are part of the
final documentation check. Apple Silicon was not executed; the commands and
dependencies are architecture-neutral, subject to the limits in
[`VERSIONS.md`](VERSIONS.md).

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
