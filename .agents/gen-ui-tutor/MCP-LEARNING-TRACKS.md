# Generative UI and agent interaction learning tracks

Use this map to teach four separate concerns. Start from the learner's actual
product boundary. A single application may use several of these technologies,
but learning one does not require implementing the other three.

## Choose the boundary

| Technology | Question it answers | Prerequisite |
|------------|---------------------|--------------|
| A2UI | How does an agent describe a UI that an approved renderer can build? | JSON, components, data binding |
| AG-UI | How does an agent exchange events and state with a user-facing app? | Client/server events, UI state |
| MCP Apps | How does an MCP server offer embedded UI in a compatible AI host? | MCP tools and resources |
| A2A | How do independent agents discover and work with each other? | Agent roles, remote task boundaries |

**A2UI — declarative UI and rendering:**

> The agent sends structured UI descriptions. The renderer validates them
> against a component catalog and builds native, approved components. Teach
> component identity, properties, data binding, user actions, validation, and
> the renderer's trust boundary. The agent does not get to supply arbitrary
> executable UI code. Begin with one form field and one action.

**AG-UI — agent and frontend communication:**

> The agent runtime and a user-facing application exchange typed events. Teach
> run start/finish, messages, tool calls, state snapshots and updates, and how
> the frontend reflects them. Begin with a mock event stream that updates a
> visible timeline. AG-UI describes communication; the frontend still owns
> rendering and user interaction.

**MCP Apps — embedded application UI:**

> An MCP server links a tool to a UI resource. A compatible host loads that
> resource in a sandboxed view and mediates communication with the server.
> Teach basic MCP first, then tool/UI linkage, host capability, sandboxing,
> and a readable tool-result fallback. Begin with one tool and one small view.
> Host support is required for the embedded view.

**A2A — independent agent communication:**

> One agent service discovers and delegates to another through an agent-facing
> task contract. Teach Agent Cards, messages, task lifecycle, artifacts, and
> trust across organizations or runtimes. Begin with one coordinator and one
> mock specialist. A2A does not define the user's UI.

## A practical sequence

1. Identify the owned surface: first-party app, compatible chat host, or no UI.
2. Show a simple ticket decision with ordinary data and a backend approval
   rule. The UI never grants approval authority by itself.
3. Add one boundary at a time: an A2UI form, an AG-UI event feed, an MCP App
   view, or an A2A specialist task, according to the learner's goal.
4. Compare the result against the same question: who sends what to whom, who
   renders it, and who checks permission before an effect?
5. Add compatibility, failure, and recovery behavior only after the basic
   exchange works.

The simplest useful combinations are also valid. AG-UI may carry agent events
to a first-party application that renders A2UI descriptions. An MCP App may
display a form inside a chat host while its server performs authorized actions.
An A2A specialist may supply data to an agent whose frontend uses AG-UI.
These are example compositions, not required stacks.

## MCP and App Bridge subtrack

The existing MCP track remains the prerequisite for MCP Apps:

1. **MCP:** host, client, server, tools, resources, and request/result flow.
   Use the [maintained MCP course](../../reference/mcp/learning/README.md).
2. **MCP Apps:** tool-linked UI resource, compatible host, embedded view,
   sandbox, and text fallback.
3. **App Bridge:** host-side bridge between the embedded view and the MCP
   server. Identify the host, bridge, iframe, UI, and server responsibilities.

Teach only the needed MCP foundations when the learner starts with the Apps
track. The App Bridge is a component of an MCP Apps host integration, not a
fifth peer protocol.

## Source and version checks

Check the relevant official source before writing a runnable example. Record
the version and the tested host or renderer; protocol support varies.

- [A2UI specification](https://a2ui.org/specification/v1.0/) and
  [component catalogs](https://a2ui.org/concepts/components/).
- [AG-UI introduction](https://github.com/ag-ui-protocol/ag-ui/blob/main/docs/introduction.mdx).
- [MCP Apps overview](https://github.com/modelcontextprotocol/ext-apps/blob/main/docs/overview.md)
  and [specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx).
- [A2A 1.0 specification](https://a2a-protocol.org/v1.0.0/specification/).

Use the `SKILL.md` learning workflow for clear explanations and small examples.
For numbered AI system-design cases, follow `ai-study-tutor` and load only the
relevant GenUI or multi-agent module.
