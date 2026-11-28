# Reusable MCP prompts

**Outcome:** Retrieve a parameterized prompt and explain why retrieval does not run a model.

**Prerequisites:** [09: Resources, URIs, and templates](09-resources.md).

## Reuse a useful interaction

Suppose support staff repeatedly need the same kind of ticket summary:
current status, confirmed facts, and missing information. A prompt component
lets the server offer a reusable interaction template.

```
prompts/list --> choose summarize_ticket
                         |
prompts/get(ticket_id) --> rendered messages
                         |
                  host chooses model use
```

The last step belongs to the host. Retrieving prompt messages does not itself
fetch a ticket, call an LLM, execute a tool, or create a summary.

## Inspect the supplied prompt

In [server.py](../fast-mcp-2026-07-28/labs/server.py), `summarize_ticket` accepts a ticket ID and
returns instructions referring to that ID. The client obtains the prompt and
checks its text. The example is deliberately simple: it does not silently read
data while generating instructions.

```python
@mcp.prompt
def summarize_ticket(ticket_id: str) -> str:
    """Prepare instructions; retrieving them does not run a model."""
    return (
        f"Summarize ticket {ticket_id}. State its status and distinguish "
        "known facts from missing information."
    )
```

A connected client retrieves the rendered messages:

```python
prompt = await client.get_prompt(
    "summarize_ticket",
    {"ticket_id": "T-100"},
)
print(prompt.messages[0].content.text)
```

The returned text is input that a host may use later. No model call appears in
this code.

A host could first read `ticket://T-100`, then retrieve the summary prompt,
then provide both to its model. That is a host workflow built from two
components. It is not a behavior the protocol automatically infers.

## Prompts versus other instruction sources

A server prompt is a discoverable component. A host's system instructions
govern its own assistant. A user request describes the user's task. Retrieved
ticket content is evidence. Keep these roles distinct when constructing model
input.

A prompt cannot override backend authorization. If a template says “close the
ticket,” the host still needs a permitted tool invocation and the service still
needs access checks.

Likewise, content embedded in a resource can include malicious instructions.
Do not treat all retrieved text as policy merely because it came through MCP.

## Parameters and versions

Choose parameters that express user intent clearly. Ticket ID and desired
summary audience are useful examples. Avoid hiding essential values in
unstructured free text when the interface can make them explicit.

Changing a template can change model behavior even when its name stays the
same. Maintain reviewed prompt content and test representative outputs at the
host layer. Protocol tests can verify returned message structure; they cannot
establish that every model will produce an accurate summary.

## When to keep a template in the host

If only one application uses a tightly coupled instruction, a host-owned
template may be easier to maintain. A server prompt is useful when several
compatible hosts should discover and reuse a service-specific interaction.
Check host support: a host may support tools but expose no prompt-picker UI.

**Worked failure:**

> A client successfully obtains the template but reports that no summary
> appeared. Inspect the host's model invocation. The prompt server fulfilled
> its retrieval contract; generation is a separate step.

**Professional articulation:**

> “MCP prompts distribute reusable interaction templates. The host remains
> responsible for selecting context and invoking the model.”

## Sources and next step

- [Archived resources and prompts example](../fastMcp-fastApi-uvicorn-ngnix-docker/3_Resources_Prompts.md)
- [Archived prompt notes](../../02-fast-mcp/04-prompts.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts) — checked 2026-11-15.

Next: [Streamable HTTP](11-streamable-http.md).

