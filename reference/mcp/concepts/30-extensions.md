# Optional extensions and deprecated features

**Outcome:** Separate core MCP from Apps, Tasks, Skills, and compatibility-only features.

**Prerequisites:** [04: Protocol versions and capability discovery](04-versions-discovery.md), [09: Resources, URIs, and templates](09-resources.md), [13: Elicitation and additional user input](13-elicitation.md).

## Core capability does not imply every experience

A client that can call a tool may be unable to render an interactive application
or manage a long-running task. Extensions add separately negotiated behavior.
Both endpoints and the host experience must support the selected extension.

## MCP Apps

MCP Apps connect tool results with interactive UI rendered by a compatible
host. They can support a ticket table or form inside the host experience.
A standalone React dashboard is not automatically an MCP App.

The UI adds another trust boundary. A browser action still needs backend
validation, caller identity, and authorization. An iframe or front-end state
must not grant access to records.

## Tasks

Tasks address operations whose lifetime exceeds an ordinary interactive call.
A durable handle lets the client inspect progress and obtain the outcome.
Current Tasks behavior belongs to an extension and differs from the earlier
experimental core feature.

Before using Tasks, define persistence, ownership, expiry, cancellation,
and what happens when a client disappears. A task handle should be scoped
to its owner and operation, not treated as unrestricted authority.

## Skills over MCP

Skills distribute reusable instructions and supporting material through an
optional extension. They are different from the workspace teaching skill
created for this course. The local teaching skill does not require a deployed
MCP Skills server.

A host may support ordinary resources while lacking dedicated Skills
discovery. Treat support as something to verify, not infer from package
installation.

## Roots, sampling, and logging

The modern revision deprecates these features while retaining compatibility
during their lifecycle window. Roots historically describe client-provided
filesystem boundaries; they are not an operating-system sandbox. Sampling
historically asks the client for model generation; it is distinct from the
server calling a provider directly. Protocol logging is distinct from ordinary
stderr logs and operational telemetry.

Consult the
[feature changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
and [extension index](https://modelcontextprotocol.io/extensions/overview)
before implementing a feature for a new service.

## A compatibility decision

If the host cannot render Apps, a tool can still return useful structured/text
content when the extension defines a suitable fallback. If a workflow requires
interactive UI and has no acceptable fallback, report incompatibility clearly.

For a large report, first ask whether a bounded synchronous result is enough.
Use a task when operation lifetime and reliability require it, not merely
because an extension exists.

**Professional articulation:**

> “We negotiate optional capabilities explicitly and design a usable fallback
> or clear incompatibility response for each required feature.”

## Sources and next step

- [Archive: _learning_resources/interactive/mcp-learning-app.tsx](../../_learning_resources/interactive/mcp-learning-app.tsx)
- [Archive: _learning_resources/requirements/01-requirements.md](../../_learning_resources/requirements/01-requirements.md)
- [Archive: conversations/chunks/08-mcp-chunk8.md](../../conversations/chunks/08-mcp-chunk8.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) — checked 2026-11-15.

Next: [Reading and migrating legacy MCP examples](31-legacy-migration.md).

