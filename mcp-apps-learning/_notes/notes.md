# MCP Apps: Progressive Learning Notes

**Goal:** Understand how an AI conversation, an MCP tool, a backend, and an
embedded UI work together.

- Read the sections in order on your first pass.
- Each section adds one part to the same hotel-search example.
- These are concept notes; the JSON examples illustrate
  message shapes, not a complete runnable application.

## Learning path

| Step                    | Question you will be able to answer                                  |
|-------------------------|----------------------------------------------------------------------|
| 1. Roles                | Who decides, executes, enforces rules, and renders?                  |
| 2. Data flows           | How do conversation, tool execution, and UI interaction differ?      |
| 3. Tool results         | What is `structuredContent`, and who uses it?                        |
| 4. UI resources         | Where does the widget come from, and how is it linked to a tool?     |
| 5. Message delivery     | How does the tool result reach JavaScript in the widget?             |
| 6. Interaction patterns | When does a user action need the LLM?                                |
| 7. Complete example     | How do these pieces work together in a hotel search?                 |
| 8. Review               | Can you explain the architecture without mixing up responsibilities? |

## 1. Start with the roles

**MCP (Model Context Protocol)** defines how an AI application communicates with
servers that expose capabilities and data. 

**MCP Apps** extends that connection with UI resources a host can display.

The **host** is the application that runs the conversation and displays the UI.
“Host” is a general role; another MCP Apps compatible application could fill it.
In this hotel example, **ChatGPT is the host**.

The **LLM (large language model)** is the model the host uses to interpret
requests and select tools.

An **MCP client** is the host's connection to an MCP server.

### Terms used in these notes

| Term          | Meaning in this guide                                                                 |
|---------------|---------------------------------------------------------------------------------------|
| UI            | What a person sees and may interact with; it can also be read-only.                   |
| UI resource   | Developer-supplied HTML, CSS, and JavaScript served by the MCP server.                |
| Webpage       | The HTML document loaded from the UI resource. It need not have a public website URL. |
| Iframe        | The embedded browser container that holds the webpage and isolates it from the host.  |
| Widget (View) | The rendered UI running in that iframe. It can be read-only or interactive.           |

From here on, **widget** means the rendered View. **Iframe** means its container;
**UI resource** means the code the host loads to create it.

### Roles at a glance

| Part                          | Responsibility                                                                  | Hotel example                                      |
|-------------------------------|---------------------------------------------------------------------------------|----------------------------------------------------|
| LLM                           | Interpret the request; select a tool and its arguments                          | Turn “king rooms in Phoenix” into search arguments |
| Host                          | Run the conversation, call tools through its MCP client, and display the widget | ChatGPT                                            |
| MCP client                    | Exchange MCP messages with the server on the host's behalf                      | Send `tools/call` and receive the result           |
| MCP server                    | Expose tools and UI resources                                                   | Offer `searchRooms` and the hotel UI resource      |
| Backend / application service | Enforce authorization and business rules                                        | Check access, availability, and booking rules      |
| Database                      | Store data and enforce database constraints                                     | Store rooms and reservations                       |
| Widget                        | Render data and handle user actions when present                                | Show room cards and handle refresh clicks          |

The backend can be a separate service or code within the MCP server. A separate
service and database are choices for this example, not MCP Apps requirements.

### How they connect

```text
                        ┌───────────────┐
User ◀─────────────────▶│ Host/Runtime  │◀──────────────▶ LLM (interprets requests
                        │ (e.g. ChatGPT)│                 and selects tools + arguments)
                        └───────┬───────┘
                                │
               tools/call       │          Host loads UI resource via MCP client
               ┌────────────────┴───────────────────────┐
               │ ▲ tool result: content                 │  Mounts iframe
               │ │ + optional structuredContent         │  Sends ui/notifications/tool-result
               ▼                                        ▼
           MCP client                           Widget in iframe
               │                                        │
               ▼                                        ▼
           MCP server                              JavaScript
             (Tool)                                     │  Reads params.structuredContent
               │                                        ▼  (if present)
               ▼                                   DOM rendering
            Backend                                     │
               │                                        ▼
               ▼                                   Visible UI
            Database                                    │ user clicks button (Pattern B)
                                                        ▼
                                                 UI JavaScript
                                                        │ tools/call via Host / MCP client
                                                        ▼
                                                    MCP tool (same server)
                                                        │ tool result via Host / MCP client
                                                        │ (includes structuredContent)
                                                        ▼
                                                 UI JavaScript
                                                        │
                                                        ▼
                                            Re-render existing widget
```

### Read the diagram in order

1. **Discover the tool and UI.** The server advertises a tool definition with
   `_meta.ui.resourceUri`, which points to a `ui://` resource. This link belongs
   to the tool definition, not to the tool result.

2. **Run the tool.** The LLM selects the tool; the host calls it through its MCP
   client. The backend applies its rules and returns data through the server.
   The tool result has `content` and may have `structuredContent`.

3. **Show the widget.** The host fetches the UI resource, loads its webpage in
   an iframe,
   and sends the completed result with `ui/notifications/tool-result`. The widget
   can read `params.structuredContent` and render it. The host may mount the
   iframe while the tool is still running.

4. **Handle a widget click (Pattern B).** Widget JavaScript calls a known tool
   through the host. The result returns to that JavaScript, which updates the
   existing widget. This click does not require the LLM to select the tool again.

**Responsibility boundary:**

- The model selects capabilities
- The application validates and executes them
- The host connects the server and widget
- The widget renders the result.

Passing data through MCP does not make it inherently trustworthy—authorization
and business rules still belong in the application.

See the
official [MCP Apps architecture and lifecycle](https://apps.extensions.modelcontextprotocol.io/api/documents/overview.html)
for the host, server, iframe, and message flow.

## 2. Separate the three data flows

### A. Conversation

```text
User text ──▶ Host (Eg. ChatGPT) ──▶ LLM
User      ◀── Host (Eg. ChatGPT) ◀── LLM reply
```

Example: “What is a king room?” may need only a conversational response.

### B. Tool execution

```text
LLM selects tool + arguments
    ──▶ Host's MCP client     ──▶ MCP server's tool ──▶ Backend ──▶ Database
    ◀── Host receives result  ◀── MCP tool          ◀── Backend ◀──
```

Example: “Show available king rooms in Phoenix” needs application data.
The host can use the result in the conversation and deliver it to a widget.

### C. UI interaction

```text
User action → Widget JavaScript ──▶ Host ──▶ MCP tool     ──▶ Backend
                  ▲                      ◀── Tool result  ◀──
                  │
                  └── Update the existing widget
```

Example: a “Refresh availability” button can request fresh data without another
LLM decision. An action such as expanding a room card can be entirely local and
need no tool call.

**Checkpoint:** A user sorts already-loaded rooms by price. Which part could do
this without contacting either the LLM or the backend?

## 3. Understand the tool result

A tool result carries the output of a tool execution. For the hotel example,
use a short text summary plus structured room data.

```json
{
  "content": [
    {
      "type": "text",
      "text": "Found 1 king room in Phoenix for October 10–13, 2026."
    }
  ],
  "structuredContent": {
    "city": "Phoenix",
    "checkIn": "2026-10-10",
    "checkOut": "2026-10-13",
    "rooms": [
      {
        "id": "room-101",
        "type": "king",
        "nightlyRate": 180,
        "currency": "USD"
      }
    ]
  }
}
```

These are illustrative values, not live availability or prices.

- **`content`** holds content blocks; this example uses text for a readable summary.
- **`structuredContent`** is an optional JSON object. Named fields let the widget
  render data without extracting it from prose.
- **`outputSchema`**, when declared on a tool, describes the expected structure
  of its structured result.

These fields are defined by the
[MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#tool-result).

Conceptually, there are two consumers:

```text
                                      ┌────▶ Conversation / model context
Tool result ──▶ Host (Eg. ChatGPT) ───┤
                                      └────▶ Widget rendering
```

Do not assume both consumers receive an identical representation. What is
included in model context depends on the host integration. Keep a useful text
summary, and treat `structuredContent` as data for rendering rather than a
privacy boundary.

**Checkpoint:** Which field should a widget read to display `nightlyRate` without
parsing the sentence “Found 1 king room…”?

## 4. Connect the tool to a UI resource

The tool supplies data. The **UI resource** supplies the webpage's HTML, CSS,
and JavaScript. The developer creates that code ahead of time; the LLM does not
need to generate it for every search. The host loads the resource to create the
widget; the resource itself is the source code.

```text
             ┌──▶ Tool: searchRooms
             │       └───▶ UI metadata points to ──▶ ui://hotel-search/app.html
MCP server ──┤            (_meta.ui.resourceUri)
             │
             └──▶ UI resource: ui://hotel-search/app.html
                      └──▶ Hotel UI code (HTML, CSS, JavaScript)
```

A resource URI is an identifier the host can ask the MCP server to read. It is
not necessarily a public website URL.

### The link belongs to the tool definition

This example advertises a tool and associates it with a UI resource:

```json
{
  "name": "searchRooms",
  "description": "Search available hotel rooms.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string"
      },
      "roomType": {
        "type": "string"
      },
      "checkIn": {
        "type": "string"
      },
      "checkOut": {
        "type": "string"
      }
    },
    "required": [
      "city",
      "roomType",
      "checkIn",
      "checkOut"
    ]
  },
  "_meta": {
    "ui": {
      "resourceUri": "ui://hotel-search/app.html"
    }
  }
}
```

The server must also serve the referenced resource. The standard UI resource
media type is `text/html;profile=mcp-app`. See the
[MCP Apps resource specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx).

The metadata describes the relationship in advance. The tool's execution result
then supplies the data, as shown in section 3. A top-level `uiResource` field in
a tool result is not the standard linkage shown here. The
[official tool registration example](https://apps.extensions.modelcontextprotocol.io/api/documents/quickstart.html#2-register-the-tool-and-ui-resource)
uses `_meta.ui.resourceUri`.

**Checkpoint:** If two searches return different rooms but use the same layout,
which changes: the UI resource, the tool result, or both?

## 5. Follow the result into the widget

An **iframe** is an embedded browser container, not the webpage itself. An MCP
Apps host loads the UI resource's webpage into a sandboxed iframe. The rendered
UI inside is the widget; the sandbox restricts its access to the host.

The simplified lifecycle is:

1. **Discover:** The host learns the tool definition and its UI resource link.
2. **Load:** The host reads the UI resource and loads its webpage into an iframe.
3. **Initialize:** The widget and host establish their communication bridge.
4. **Deliver:** The host sends tool input and the completed tool result.
5. **Render:** Widget JavaScript updates the webpage's DOM to show the result.

The host can load the widget while the tool is still running. This is not necessarily
“wait for all data, then create the iframe.” See the
[MCP Apps lifecycle](https://apps.extensions.modelcontextprotocol.io/api/documents/overview.html#lifecycle).

### The message contract

The bridge carries **JSON-RPC 2.0** messages over the browser's **`postMessage`**
mechanism. JSON-RPC provides the message structure; `postMessage` carries it
between the widget and host.

For the host-delivered tool result, the notification method is
`ui/notifications/tool-result`. Its `params` contains a tool result:

```json
{
  "jsonrpc": "2.0",
  "method": "ui/notifications/tool-result",
  "params": {
    "content": [
      {
        "type": "text",
        "text": "Found 1 king room."
      }
    ],
    "structuredContent": {
      "rooms": [
        {
          "id": "room-101",
          "type": "king",
          "nightlyRate": 180,
          "currency": "USD"
        }
      ]
    }
  }
}
```

A **notification** has no request `id` and expects no response. The tool data is
inside `params`; it is not the whole message. See the
[tool-result notification contract](https://apps.extensions.modelcontextprotocol.io/api/interfaces/app.McpUiToolResultNotification.html).

```text
Host (Eg. ChatGPT)
      │
      ▼
  Bridge message
JSON-RPC tool-result notification
      │
      ▼
Widget JavaScript ──▶ DOM update ──▶ Visible room card
```

The **DOM (Document Object Model)** is the browser's representation of the page.
The widget needs the result's data contract to render it; it does not need the
full LLM conversation.

In the MCP Apps JavaScript SDK, `app.ontoolresult` handles these notifications.
Register the handler before `app.connect()` so it can receive the initial result.
See
the [official widget example](https://apps.extensions.modelcontextprotocol.io/api/documents/quickstart.html#3-build-the-view).

## 6. Distinguish LLM-driven and UI-driven interaction

| Pattern         | Trigger                           | Who selects the tool?                              | What happens to the UI?                        |
|-----------------|-----------------------------------|----------------------------------------------------|------------------------------------------------|
| LLM-driven      | Natural-language request          | LLM selects a tool; host executes it               | Host can display the linked widget             |
| UI-driven       | Button, filter, or other control  | Widget code requests a known tool through the host | Widget handles the response and updates itself |
| Local UI change | Expand a card or sort loaded data | No tool is needed                                  | Widget changes its local state                 |

### LLM-driven: start from an intent

```text
User request (“Show king rooms”) ──▶ Host (Eg. ChatGPT) ──▶ LLM selects searchRooms tool
                                      │
                                      ├──▶ Host calls tool ──▶ Tool result ──▶ Host
                                      │
                                      └──▶ Host displays linked widget and delivers result
```

A separate render tool is an optional application design: the model could call a
data tool, then a UI-linked tool. It is not a required second step. One tool can
both return room data and have UI metadata.

The LLM influences what is shown through its tool choice. The host performs the
actual resource loading, iframe mounting, and message delivery.

### UI-driven: start from an explicit control

```text
“Refresh” click ──▶ Widget ──▶ Host   ──▶ searchRooms
                    ▲   ▲
                    │   │
                    │   └───── Result ◀──
                    │
                    └── Render updated room data
```

With the SDK, `app.callServerTool()` returns the result to the widget's calling
code. Handle that returned result; do not assume it will also arrive through
`app.ontoolresult`.
The [official quickstart](https://apps.extensions.modelcontextprotocol.io/api/documents/quickstart.html#3-build-the-view)
demonstrates these two paths separately.

Tool access depends on host support and tool visibility. UI-driven calls still
need backend authorization and business-rule validation.

**Checkpoint:** Does clicking “Refresh” require the LLM to choose the same tool
again? Does bypassing an LLM decision also bypass backend checks?

## 7. Put it together: hotel search

User request: **“Show me king rooms in Phoenix for October 10–13, 2026.”**

1. The **LLM** interprets the request and selects `searchRooms` with city, room
   type, and dates.
2. The **host** sends the tool call through its MCP client to the **MCP server**.
3. The **tool** calls the **backend**, which applies authorization and search rules.
4. The **backend** queries **PostgreSQL** and returns room data.
5. The **tool** returns a summary and `structuredContent` to the **host**.
6. Using the tool's UI metadata, the **host** loads the hotel widget if needed and
   delivers the result. UI loading can overlap tool execution.
7. The **widget** renders room cards. The **LLM** may also produce a text response
   from the information made available to it.
8. A **user interaction** can update local UI state or request another tool call
   through the host.

In an MCP Apps-capable host, this can produce chat text plus a hotel widget.
A host without this extension can still use a suitable text tool result.
See [progressive enhancement](https://apps.extensions.modelcontextprotocol.io/api/documents/overview.html#progressive-enhancement).

## 8. Review and explain it professionally

**Professional articulation:**

> “Our MCP server exposes business capabilities and links tools to UI resources.
> The model selects tools, the host executes calls and delivers results, and the
> widget renders the data. Authorization and business rules remain in our
> application layer.”

### Checkpoint answers

| Section         | Expected understanding                                                            |
|-----------------|-----------------------------------------------------------------------------------|
| 2. Data flows   | The widget can sort data it already has.                                          |
| 3. Tool results | Read the room's `nightlyRate` from `structuredContent`.                           |
| 4. UI resources | The tool result changes; the UI resource can stay the same.                       |
| 6. Interactions | Refresh can call a tool without another LLM decision. Backend checks still apply. |

### Corrections to keep in mind when reading other notes

- **Tool selection is not UI mounting.** The host embeds the widget.
- **Structured data does not identify a UI by itself.** Tool metadata supplies
  the UI resource link.
- **A separate render tool is optional.** A data-returning tool can already be
  linked to a widget.
- **A widget's tool call goes through the host.** The widget does not need the LLM to
  interpret each button click.
- **MCP is a protocol, not a guarantee of business correctness.** Validate inputs,
  permissions, and application rules at the appropriate boundaries.

*Editorial note: Protocol details were checked against the linked official documentation on September 26, 2026.*
