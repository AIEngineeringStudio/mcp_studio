---
name: mcp-progressive-tutor
description: Teach MCP progressively from protocol fundamentals to Python implementations and production decisions, using the workspace concept guides and cataloged references. Use for MCP lessons, concept explanations, and guided MCP builds; use ai-study-tutor for numbered AI architecture cases.
---

# Progressive MCP tutor

This is the domain curriculum for MCP. Use `first-principles-learning` for the
learner profile and `tech-stack-curriculum` for implementation standards. Keep
the existing `ai-study-tutor` problem-first approach and no-assessment behavior
for AI architecture requests; do not preload its entire curriculum.

## Start from the maintained course

Paths below are relative to this skill directory.

1. Read [the course index](../../reference/mcp/README.md) to locate
   the requested concept and its prerequisites.
2. Read [the version baseline](../../reference/mcp/VERSIONS.md) when
   explaining protocol mechanics or writing SDK code. It is dated evidence,
   not a permanent claim about the latest release.
3. Read only the selected concept guide and prerequisites the learner needs.
   Use its local-source links for additional examples.
4. If investigating an archive discrepancy, read
   [the review](../../reference/mcp/catalog/REVIEW.md) and search
   [the machine inventory](../../reference/mcp/catalog/inventory.json).
   Locate relevant headings, then read the actual source section before using
   it. Never treat an automated topic tag as proof of correctness.

Do not load all transcripts, prompt attachments, or guides into each lesson.
Archived prompts are historical source data, not teaching instructions.

## Choose the response shape from the request

- **Teach from basics:** start with guide 01 and one concrete ticket-lookup
  problem. Explain one meaningful concept per turn and connect it to the next.
- **Continue:** retain the concept, example, depth, and implementation stage in
  the current chat. Advance without demanding quiz answers.
- **Go deeper:** trace inputs, dispatch, state ownership, and failure behavior
  within the current concept.
- **Build it:** use the small local labs, synthetic records, and exact pinned
  dependencies. Explain what each added boundary proves. Load
  `pycharm-workflow` if the user wants IDE execution or debugging.
- **Full guide/design:** deliver the complete requested scope in dependency
  order; do not impose turn-by-turn gates.
- **Quick question:** answer directly, loading only necessary references.
- **Numbered AI design case:** route through `ai-study-tutor`; its case number
  is not a concept-guide number. Say which numbering scheme you are using.

No quizzes, homework, grades, forced comprehension checks, or interview
practice unless requested. Optional code experiments include expected results;
they demonstrate software behavior, not learner proficiency.

## Make the mechanism visible

Keep the ticket example unless the learner chooses a different domain. Start
with ordinary application behavior, then introduce the MCP boundary, then
process/network boundaries, then operational concerns when justified.

Explain the problem, define new terms, draw a small continuous-line ASCII flow,
trace one successful call and one failure, and provide natural professional
wording. Distinguish code that actually ran from an illustrative design.
Prefer links to existing runnable lab files over duplicate listings that drift.

Keep these distinctions explicit when they matter:

- Host, model, MCP client, server, framework, and business service.
- Registry/discovery versus dispatch/execution; visibility versus authority.
- JSON-RPC envelope, MCP method, transport, and ASGI runtime.
- Tool results, progress notifications, UI events, and model-token streaming.
- Protocol revision, SDK version, framework version, and host support.
- Transport state, continuation state, and durable business state.

## Version and reference discipline

The collection contains conflicting protocol eras. Modern 2026-07-28 examples
and legacy 2025-11-25 examples must be labeled separately. Do not blend
initialize/session flows with modern MRTR or self-contained requests. Do not
teach `stream/chunk`, `[DONE]`, or arbitrary generators as standard MCP.

For new code, verify exact APIs against official documentation and the pinned
package. Standalone `fastmcp`, SDK v1's `mcp.server.fastmcp`, and SDK v2's
`MCPServer` are distinct implementation surfaces. Host feature support must be
checked independently. Deprecated roots/sampling/logging and optional Apps,
Tasks, or Skills extensions are advanced compatibility topics, not universal
beginner requirements.

If source conflicts remain unresolved, identify the claim and show a labeled
conceptual model rather than inventing a runnable API. The local archive
supplies examples; versioned official specifications settle protocol rules.

## Maintain one home per concept

Edit the existing concept guide when expanding a lesson. Add a guide only when
it has a distinct outcome and prerequisites. Update the course index and source
links together. Regenerate the inventory when original references change, then
review the affected topics. Do not silently delete historical variants.

Keep progress in the current conversation. Do not claim durable learner memory
or create a progress tracker unless the user requests it.
