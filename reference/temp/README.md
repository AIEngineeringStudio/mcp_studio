# MCP learning library

Start with the [learning path](learning/README.md). It presents individual
concept guides in prerequisite order, using one synthetic ticket service as
the running example.

The original collection is preserved as source material. Use the
[review and source map](catalog/REVIEW.md) to understand which sources are
useful and which need correction. The [complete inventory](catalog/INVENTORY.md)
lists every original file; [inventory.json](catalog/inventory.json) also
contains content hashes, headings, topic tags, and duplication evidence.

The workspace teaching skill is
[mcp-progressive-tutor](../../.agents/mcp-progressive-tutor/SKILL.md).
Ask, for example, `Use mcp-progressive-tutor to teach me MCP from basics`,
`Continue`, or `Explain concept 13 in more depth`.

## How to maintain this library

Maintain each concept in its individual guide. Link to that guide when another
lesson depends on it. Preserve transcripts for provenance; adding another
transcript does not automatically change the course.

When adding references, run this command from the workspace root:

```bash
python3 reference/mcp/catalog/build_catalog.py
```

Then review the new material, update the source map, and revise only the
affected guides. The generator updates the inventory, not the curated lessons.
Check the [version baseline](learning/VERSIONS.md) before changing examples.
Protocol revisions and framework versions are different version numbers.

**Review boundary:**

> The catalog covers every original file. Text was scanned in full for inventory
> and overlap analysis, then reviewed structurally and thematically with selected
> close reading. It is not a line-by-line correctness certification of every
> archived example. Archived programs and visual assets remain unverified unless
> a review note explicitly says otherwise.
