# Testing Any MCP App with MCP Inspector

## A reusable beginner guide, test strategy, and checklist

This guide teaches a repeatable method for testing **any MCP App**. Your current
`say_hello` server is used only as the first worked example.

The goal is not merely to answer “does the page appear?” The goal is to locate
failures precisely across the server, MCP protocol, App bridge, UI, security,
and user-experience layers.

This is a **concept exercise**. Docker, authentication, and deployment are not
prerequisites. Production checks are identified separately.

Version check: **September 26, 2026**.

- Project MCP Python SDK: `mcp[cli]==2.2.0`
- MCP Inspector used below: `2.8.0`
- Inspector 2.x requires Node.js `22.19.0` or newer
- This computer has Node.js `24.12.0`

The commands work unchanged on Intel (`x86_64`) and Apple Silicon (`arm64`)
Macs.

## How to use this guide

For your **first Inspector session**, follow sections 3–13, then section 25.
That path covers inventory, startup, connection, tools, results, resources, and
rendering without introducing every advanced feature at once.

For a **complete review of another MCP App**, continue through sections 14–24
and complete the reusable report in section 27. Test only features the App
actually implements, but always include security, accessibility, fallback, and
cross-host checks.

---

## 1. The system you are testing

An MCP App has three main parts:

```text
┌──────────────────┐       MCP protocol       ┌──────────────────┐
│ Host             │ <----------------------> │ MCP server       │
│ - MCP client     │                          │ - tools          │
│ - App bridge     │                          │ - UI resources   │
│ - iframe         │                          │ - business logic │
└────────┬─────────┘                          └──────────────────┘
         │ postMessage
         ▼
┌──────────────────┐
│ View / MCP App   │
│ HTML/CSS/JS      │
└──────────────────┘
```

Definitions:

- **Server**: exposes tools and `ui://` resources.
- **Host**: connects to the server and embeds the App.
- **View** or **App**: the HTML/CSS/JavaScript running in a sandboxed iframe.
- **App bridge**: carries messages between the host and iframe.
- **MCP Inspector**: a development host used to inspect and exercise these
  boundaries.

Inspector can verify most behavior. A real conversational host is still needed
for final portability and model-behavior testing.

---

## 2. The universal testing ladder

Always test from the bottom upward:

| Level                | Test question                                          | Evidence                                   |
|----------------------|--------------------------------------------------------|--------------------------------------------|
| 1. Process           | Did the server start?                                  | No startup error; port is listening        |
| 2. Connection        | Can Inspector speak MCP to it?                         | Connected status                           |
| 3. Discovery         | Are the correct tools/resources advertised?            | Lists and metadata are correct             |
| 4. Tool contract     | Do valid and invalid inputs behave correctly?          | Expected result or validation error        |
| 5. Resource contract | Can the UI resource be read?                           | Correct URI, MIME type, HTML, metadata     |
| 6. Rendering         | Does the View initialize and render?                   | App reaches ready state                    |
| 7. Data delivery     | Does input/result data reach the View?                 | UI matches tool arguments/results          |
| 8. Interaction       | Do buttons and forms perform the right action?         | Local update or expected protocol call     |
| 9. Host integration  | Do theme, display, links, and chat actions work?       | Correct host-visible behavior              |
| 10. Resilience       | Does the App handle errors and lifecycle events?       | Useful recovery state; no stale UI         |
| 11. Security         | Are sandbox, CSP, permissions, and visibility correct? | Least privilege; blocked undeclared access |
| 12. Portability      | Does it work in another compliant host?                | Same essential behavior                    |

Why this order matters:

```text
Tool call passes + iframe fails
        => do not debug business logic first

Resource read passes + App is blank
        => inspect HTML, bridge initialization, CSP, and browser console

App renders + button does nothing
        => inspect App-to-host messages and the target tool
```

---

## 3. Create a test inventory before opening Inspector

For every App-enhanced tool, record this information. Do not rely on memory.

### Test inventory template

| Item                        | Example value                                                   |
|-----------------------------|-----------------------------------------------------------------|
| Server start command        | `uv run --locked mcp run server.py --transport streamable-http` |
| MCP endpoint                | `http://127.0.0.1:8000/mcp`                                     |
| Transport                   | Streamable HTTP                                                 |
| App tool                    | `search_rooms`                                                  |
| Valid input                 | `{"city":"Phoenix","guests":2}`                                 |
| Invalid input               | `{"city":"Phoenix","guests":0}`                                 |
| UI resource URI             | `ui://hotel/search.html`                                        |
| Expected MIME type          | `text/html;profile=mcp-app`                                     |
| Expected text result        | `Found 3 rooms.`                                                |
| Expected structured fields  | `city`, `rooms`, `currency`                                     |
| App-only tools              | `refresh_rooms`, `save_favorite`                                |
| External domains            | Images, API, frames, fonts                                      |
| Requested permissions       | Clipboard, camera, microphone, geolocation                      |
| Supported display modes     | Inline, fullscreen, picture-in-picture                          |
| Expected local-only actions | Sort and expand a card                                          |
| Expected host actions       | Open link, send message, update context                         |

For your current App:

| Item                      | Current value              |
|---------------------------|----------------------------|
| App tool                  | `say_hello`                |
| Valid input               | `{}`                       |
| UI resource URI           | `ui://hello/app.html`      |
| Expected text result      | `Hello from the MCP tool.` |
| Expected rendered heading | `Hello from an MCP App`    |

---

## 4. Prepare the environment

Move into the example project:

```bash
cd /Users/sreedhar/workspace/GitHub/AIEngineeringStudio/mcp_studio/mcp-apps-learning
```

Check the tools:

```bash
uv --version
node --version
npm --version
```

Expected on this computer:

```text
uv 0.10.9
v24.12.0
11.11.1
```

The exact npm version can differ. Node.js must be at least `22.19.0` for the
pinned Inspector.

---

## 5. Start a server under test

Use **Terminal 1** for the MCP server.

For the current Python example:

```bash
cd /Users/sreedhar/workspace/GitHub/AIEngineeringStudio/mcp_studio/mcp-apps-learning
uv run --locked mcp run server.py --transport streamable-http
```

Expected:

```text
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

Leave the process running.

### Adapting this step to another server

Use that project’s documented command. Record the **actual MCP endpoint**, not
only its base URL. A base server may run at:

```text
http://127.0.0.1:8000
```

while the MCP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

Pass condition:

- Startup finishes without a traceback.
- The server remains running.
- You know its MCP endpoint and transport.

---

## 6. Start Inspector

Use **Terminal 2**:

```bash
npx --yes @modelcontextprotocol/inspector@2.8.0 \
  --server-url http://127.0.0.1:8000/mcp \
  --transport http
```

Inspector prints a browser URL containing a temporary token. Open the complete
printed URL if the browser does not open automatically.

For another Streamable HTTP server, replace only the `--server-url` value with
the endpoint from its test inventory.

### Manual connection settings

If automatic connection does not occur:

| Setting      | Value                                                 |
|--------------|-------------------------------------------------------|
| Transport    | HTTP or Streamable HTTP                               |
| Server URL   | The complete endpoint, including `/mcp` when required |
| Protocol era | Auto                                                  |

Select **Connect**.

Pass condition:

- Inspector shows **Connected**.
- Server logs show successful MCP requests.

---

# Part I — Tests for every MCP App

## 7. Test connection and capabilities

### What to do

1. Confirm the connection status is **Connected**.
2. Inspect the server information and advertised capabilities.
3. Confirm MCP Apps support was negotiated.
4. Record the server name and protocol version in the test report.

The exact protocol version can vary through negotiation. A different version is
not automatically a failure.

### What this proves

The network, transport, and basic MCP conversation work. It does not prove that
any tool or App works.

---

## 8. Test tool discovery and metadata

### What to do

1. Open **Tools**.
2. Refresh the list.
3. Select each tool that should have a UI.
4. Inspect its name, description, input schema, output schema, annotations, and
   `_meta`.

### Verify for every App tool

- Tool name is stable and unique.
- Description tells the model when to use it.
- Required and optional arguments are correct.
- Types, enums, defaults, and constraints are correct.
- `_meta.ui.resourceUri` is an absolute `ui://` URI.
- Visibility is intentional.
- The referenced resource actually exists.

Expected linkage shape:

```json
{
  "name": "search_rooms",
  "_meta": {
    "ui": {
      "resourceUri": "ui://hotel/search.html"
    }
  }
}
```

### Test app-only visibility

Tools used only by buttons or forms can use app-only visibility. Verify that:

- The App can call them.
- They do not clutter the model’s available tool list in a real host.
- Calls from an unauthorized App or different server are rejected.

Pass condition: every advertised tool matches the intended contract and points
to a valid UI resource.

---

## 9. Test the tool contract

Do not test only the happy path.

### A. Valid inputs

For each meaningful input category, run one valid example:

- Minimum valid values
- Typical values
- Maximum allowed values
- Optional arguments omitted
- Optional arguments supplied
- Every enum choice
- Unicode text, such as `José`, `東京`, or emoji
- Dates and time zones when applicable

Verify:

- The result is correct.
- `content` contains a useful text fallback.
- `structuredContent` matches the output schema when used.
- Sensitive or internal data is absent.
- Repeating a read-only call is safe.

### B. Invalid inputs

Try:

- Missing required field
- Wrong type
- Empty string
- Out-of-range number
- Invalid enum
- Malformed date
- Unexpected extra field, if the schema forbids it
- Very long input

Expected: a clear validation or tool error. The server must not crash.

### C. Business failures

Test valid syntax that cannot succeed:

- Record not found
- No results
- Conflict or duplicate
- Permission denied
- Dependency unavailable
- Rate limit or timeout

Expected: a safe, actionable result. Technical stack traces should not be sent
to the user.

---

## 10. Test text and structured results separately

An MCP tool result can serve two audiences:

```text
Tool result
   ├── content            -> readable fallback / model context
   └── structuredContent  -> reliable data for UI rendering
```

For a result like:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Found 1 room."
    }
  ],
  "structuredContent": {
    "rooms": [
      {
        "id": "101",
        "price": 180,
        "currency": "USD"
      }
    ]
  }
}
```

verify:

- The text makes sense without the UI.
- The UI does not parse prose to find `price`.
- Required structured fields exist.
- Field types match the output schema.
- Empty arrays, `null`, zero, and false are handled correctly.
- Unknown future fields do not break the App.
- Large results do not freeze the View.

Pass condition: the text fallback is useful and the structured result is stable
enough for code to consume.

---

## 11. Test the UI resource contract

Open **Resources** and read the URI linked from the tool.

Verify:

| Check                    | Expected                        |
|--------------------------|---------------------------------|
| URI scheme               | `ui://`                         |
| MIME type                | `text/html;profile=mcp-app`     |
| Content                  | Complete valid HTML document    |
| Encoding                 | UTF-8 content renders correctly |
| Title/description        | Useful when supplied            |
| `_meta.ui.csp`           | Only required domains           |
| `_meta.ui.permissions`   | Only required capabilities      |
| `_meta.ui.domain`        | Intentional, if used            |
| `_meta.ui.prefersBorder` | Intentional, if used            |

Also verify that the resource contains no embedded secret, access token, or
private server configuration.

### Negative resource tests

In a temporary branch or dedicated test server, verify graceful failure for:

- Tool points to a missing resource
- URI is not `ui://`
- MIME type is wrong
- HTML is empty or invalid
- CSP omits a required domain

Some SDKs reject invalid registration at startup. That is a successful
fail-fast behavior.

---

## 12. Test initial App rendering

### What to do

1. Open **Apps**.
2. Select an App-enhanced tool.
3. Enter valid arguments.
4. Select **Open App**.
5. Observe the App status and browser console.

### Verify

- Loading state appears when execution is not immediate.
- The iframe reaches a ready state.
- No JavaScript, bridge, CSP, or sandbox errors appear.
- The App shows the correct initial content.
- It does not briefly display stale data from a previous invocation.
- The layout fits its container.

The host may fetch the UI resource before or after the tool call because hosts
may prefetch and cache App resources.

---

## 13. Test host-to-App data delivery

Interactive Views should listen for tool input and result delivery.

### Tool input

Verify that the View receives the final arguments and renders the correct state.
If the App supports partial input, verify that partial fields are treated only
as previews and are never used for critical actions.

### Tool result

Verify that the View:

- Receives the completed tool result.
- Reads `structuredContent` for structured UI data.
- Handles a text-only result.
- Handles an error result.
- Replaces loading state with final state.
- Ignores or safely handles unknown fields.

### Repeat-invocation test

Call the same App tool twice with different inputs:

```text
Call 1: city = Phoenix
Call 2: city = Boston
```

Expected: the second App instance or update shows Boston data, never mixed with
Phoenix data.

---

## 14. Classify and test every user interaction

Every button, link, and form must belong to one of these categories:

| Interaction type        | Example                         | Expected protocol traffic |
|-------------------------|---------------------------------|---------------------------|
| Local UI action         | Sort loaded rows                | None                      |
| App-to-server tool call | Refresh data                    | `tools/call`              |
| Conversation action     | Ask assistant about selection   | `ui/message`              |
| Model-context update    | Provide state for a future turn | `ui/update-model-context` |
| Host action             | Open external documentation     | `ui/open-link`            |
| Display action          | Enter fullscreen                | `ui/request-display-mode` |

Use Inspector’s protocol history to verify that each action produces exactly
the intended traffic.

### Local-only action tests

For sorting, filtering, expanding, tabs, or client-side validation:

- The UI changes immediately.
- No MCP tool call occurs.
- Existing data is not mutated unexpectedly.
- Keyboard interaction also works.

### App-to-server tool-call tests

For refresh, save, delete, submit, or paginate:

- Correct tool name and arguments are sent.
- Loading and disabled states prevent accidental duplicate actions.
- Success updates the UI.
- Failure preserves recoverable user state.
- Destructive actions require appropriate confirmation.
- App-only tool visibility is enforced when intended.

---

## 15. Test App-to-host features

Not every App implements every feature. Test only declared or implemented
features.

### Send a chat message

Trigger the UI action that sends a message.

Verify:

- The message content and role are correct.
- The host asks for consent when its policy requires it.
- One click produces one message.
- Failure is visible to the user.

### Update model context

Verify that:

- Only useful, non-sensitive information is added.
- Later model turns receive the intended context.
- Repeated updates have predictable replacement or accumulation behavior.
- Stale context is not presented as current state.

### Open an external link

Verify that:

- The exact intended URL opens.
- User-generated URL values cannot create unsafe schemes.
- The App does not navigate or escape the host iframe unexpectedly.

### Read a server resource

If the App reads another MCP resource, verify the URI, returned type, error
state, and authorization boundary.

---

## 16. Test host context and presentation

Hosts provide environment information to the View. Test each field your App
uses.

### Theme

- Light theme is readable.
- Dark theme is readable.
- A live theme change updates the App without reload.
- CSS uses host variables with sensible fallbacks.

### Locale and timezone

- Dates use the host locale and timezone.
- Numbers and currency are formatted correctly.
- Right-to-left or long translated text does not break the layout when relevant.
- Business calculations remain server-controlled; locale changes presentation,
  not stored values.

### Container and safe area

- Narrow, medium, and wide widths work.
- Long content wraps rather than clipping.
- The App respects maximum height and safe-area insets.
- Resize notifications do not cause loops or excessive updates.

### Display modes

For each mode the View declares:

- `inline` layout works.
- `fullscreen` layout works when host and App support it.
- `pip` works when host and App support it.
- Unsupported requests leave the App usable.
- The App uses the mode returned by the host, not merely the mode requested.

Inspector may not expose a manual control for every host-context field. Use the
official `basic-host` or a real supported host for any remaining checks.

---

## 17. Test loading, cancellation, teardown, and recovery

### Slow tool

Use a test mode or stub that responds slowly.

Expected:

- Loading feedback appears.
- Controls do not submit duplicate calls.
- The UI remains responsive.

### Cancellation

Cancel a running tool when the host supports it.

Expected:

- The App handles the cancellation notification.
- Loading ends.
- Partial data is not presented as final data.
- Retry is possible when appropriate.

### Teardown

Close or replace the App.

Expected:

- Timers, observers, subscriptions, and pending requests are cleaned up.
- Temporary state is saved only when intended.
- Reopening the App creates a clean instance.

### Reconnection

1. Open the App.
2. Stop the server.
3. Trigger a server-dependent action.
4. Restart the server.
5. Reconnect and retry.

Expected: a clear disconnected/error state followed by successful recovery.

---

## 18. Test security boundaries

### Content Security Policy (CSP)

MCP Apps are restrictive by default. Inventory every external origin used by
the built View:

- `connectDomains`: API calls, fetch, WebSocket
- `resourceDomains`: scripts, styles, fonts, images, media
- `frameDomains`: nested iframes

Tests:

1. Required declared origins work.
2. An undeclared origin is blocked.
3. No wildcard is used merely to make development easier.
4. Development-only domains are absent from production metadata.

### Permissions

For clipboard, camera, microphone, or geolocation:

- The permission is declared only if needed.
- It is requested after a clear user action.
- Denial leaves the App usable or gives a clear explanation.
- The App does not repeatedly prompt.

### Data and secrets

- No secrets appear in HTML, JavaScript, tool results, logs, or model context.
- Server-side authorization is enforced on every tool call.
- The App cannot call tools outside its allowed server/visibility boundary.
- User-controlled HTML and URLs are safely handled.
- Error messages do not expose stack traces or internal paths.

---

## 19. Test accessibility and usability

Protocol correctness is not enough. Test the App as a user interface.

### Keyboard

- Every control is reachable with `Tab` and `Shift+Tab`.
- Buttons activate with keyboard controls.
- Focus is visible.
- Focus does not become trapped unexpectedly.
- Dialog focus returns to the initiating control.

### Semantics

- The page has one useful main heading.
- Form fields have labels.
- Buttons have meaningful names.
- Errors are associated with their fields.
- Dynamic status changes are announced appropriately.

### Visual quality

- Text has sufficient contrast in light and dark themes.
- Zoom to 200% does not hide essential controls.
- Long values and empty states are readable.
- Color is not the only signal for success or failure.
- Motion respects reduced-motion preferences when animation exists.

### Content states

Test at least:

- Loading
- Empty
- One item
- Many items
- Long text
- Partial data
- Error
- Success

---

## 20. Use the protocol and browser consoles together

Inspector’s views answer different questions:

| Surface         | Use it to answer                              |
|-----------------|-----------------------------------------------|
| Tools           | Was the tool advertised correctly?            |
| Resources       | Can the host read the UI template?            |
| Apps            | Does the complete View lifecycle work?        |
| Protocol        | Which MCP or App message was sent?            |
| Network         | Did the HTTP request succeed?                 |
| App logs        | What did the View report?                     |
| Browser console | Did JavaScript, CSP, or iframe behavior fail? |

Typical protocol operations include:

```text
tools/list
tools/call
resources/list
resources/read
ui/initialize
ui/notifications/tool-input
ui/notifications/tool-result
```

Depending on protocol era and feature use, you may also see partial input,
cancellation, host-context change, messages, model-context updates, display
requests, size changes, and teardown.

Do not require one fixed message order when the specification permits resource
prefetching or optional notifications.

---

## 21. Repeat protocol checks with Inspector CLI

The CLI cannot visually judge an iframe. It is excellent for repeatable
connection, schema, tool, result, and resource checks.

The commands below are fully runnable for the current server. For another
server, substitute its endpoint, tool name, arguments, and resource URI from
the test inventory.

### Connection probe

```bash
npx --yes @modelcontextprotocol/inspector@2.8.0 --cli \
  --server-url http://127.0.0.1:8000/mcp \
  --transport http \
  --method initialize
```

### List tools and App information

```bash
npx --yes @modelcontextprotocol/inspector@2.8.0 --cli \
  --server-url http://127.0.0.1:8000/mcp \
  --transport http \
  --method tools/list \
  --app-info
```

### Call a tool

```bash
npx --yes @modelcontextprotocol/inspector@2.8.0 --cli \
  --server-url http://127.0.0.1:8000/mcp \
  --transport http \
  --method tools/call \
  --tool-name say_hello \
  --tool-args-json '{}' \
  --format json
```

### List resources

```bash
npx --yes @modelcontextprotocol/inspector@2.8.0 --cli \
  --server-url http://127.0.0.1:8000/mcp \
  --transport http \
  --method resources/list
```

### Read an App resource

```bash
npx --yes @modelcontextprotocol/inspector@2.8.0 --cli \
  --server-url http://127.0.0.1:8000/mcp \
  --transport http \
  --method resources/read \
  --uri ui://hello/app.html
```

For automation, assert stable fields rather than comparing the entire output.
For example, check the tool name, resource URI, MIME type, error state, and
specific structured-result fields.

---

## 22. Know when Inspector is not enough

Use three complementary environments:

| Environment              | Best use                                                                |
|--------------------------|-------------------------------------------------------------------------|
| Inspector                | Protocol inspection, manual tool calls, resource reading, App rendering |
| `basic-host`             | Reference host behavior and focused App-bridge debugging                |
| Real conversational host | Model selection, consent UX, portability, real conversation context     |

The official `basic-host` can be started from the MCP Apps repository:

```bash
git clone --branch v2.0.0 --depth 1 \
  https://github.com/modelcontextprotocol/ext-apps.git
cd ext-apps
npm install
cd examples/basic-host
SERVERS='["http://127.0.0.1:8000/mcp"]' npm start
```

Open:

```text
http://localhost:8080
```

For a remote host, `localhost` is not reachable from the host’s servers. Use a
proper development tunnel only when needed, treat the URL as externally
reachable, and do not expose sensitive tools or data.

---

## 23. Cross-host portability test

After Inspector tests pass, connect the App to at least one intended real host.

Verify:

- The model selects the correct tool from a natural-language request.
- The host renders the same essential data.
- Unsupported optional features degrade gracefully.
- Consent prompts are understandable.
- App-only tools remain hidden from the model.
- Theme, width, and display modes do not assume Inspector’s layout.
- The text fallback remains useful when UI support is absent.

Do not require pixel-identical output across hosts. Require correct behavior,
readability, and preserved security boundaries.

---

## 24. Failure-location decision tree

```text
Server starts?
├─ No  -> fix imports, configuration, registration, or port conflict
└─ Yes
   |
   Inspector connects?
   ├─ No  -> check endpoint, transport, auth, network, and protocol era
   └─ Yes
      |
      Tool listed?
      ├─ No  -> check tool registration and negotiated capabilities
      └─ Yes
         |
         Tool call succeeds?
         ├─ No  -> check schema, validation, authorization, business logic
         └─ Yes
            |
            UI resource reads?
            ├─ No  -> check URI match, registration, MIME type
            └─ Yes
               |
               App renders?
               ├─ No  -> check HTML, bridge init, CSP, sandbox, console
               └─ Yes
                  |
                  Data correct?
                  ├─ No  -> check input/result handlers and schema mapping
                  └─ Yes
                     |
                     Interaction works?
                     ├─ No  -> check event handler and App-to-host request
                     └─ Yes -> run resilience, security, accessibility,
                               and cross-host tests
```

---

# Part II — Worked example: the current `say_hello` App

## 25. Expected contract

Your current server contains:

```text
Tool:       say_hello
Input:      {}
Result:     Hello from the MCP tool.
UI URI:     ui://hello/app.html
UI title:   Hello MCP App
Heading:    Hello from an MCP App
Paragraph:  This HTML came from an MCP resource.
```

### Manual test

1. Start the server using section 5.
2. Start Inspector using section 6.
3. In **Tools**, confirm `say_hello` exists.
4. Call it with `{}`.
5. Confirm `Hello from the MCP tool.` is returned.
6. In **Resources**, read `ui://hello/app.html`.
7. Confirm MIME type `text/html;profile=mcp-app`.
8. In **Apps**, select `say_hello` and choose **Open App**.
9. Confirm the heading and paragraph appear.
10. In **Protocol**, identify tool discovery, resource reading, and tool call.

### Current limitation

This App is static. The tool result and HTML are independent:

```text
Python tool result  -> "Hello from the MCP tool."
Static HTML         -> "Hello from an MCP App"
```

The App does not yet use JavaScript to receive tool input or
`structuredContent`. Therefore, changing the Python result will not
automatically change the heading.

That is not a test failure. It is the boundary of the current exercise.

---

## 26. Recommended progression for future test Apps

Add and test one capability at a time:

1. **Typed input** — `say_hello(name: str)`.
2. **Structured output** — return `{"greeting":"Hello, Sreedhar"}`.
3. **Dynamic rendering** — View reads the result and updates the DOM.
4. **Local action** — toggle formatting without a server call.
5. **App-only tool** — refresh or save through `tools/call`.
6. **Error state** — force a controlled tool failure.
7. **Host context** — respond to theme and container changes.
8. **Display mode** — request fullscreen when available.
9. **Security test** — allow one origin and prove another is blocked.
10. **Lifecycle** — handle cancellation and teardown.

This progression keeps each failure attributable to one new boundary.

---

## 27. Reusable test report

Copy this section for each App tool.

```text
MCP App test report

Date:
Tester:
Server version:
Inspector version:
Host/browser:
Transport:
Endpoint:
Tool:
UI resource:

[ ] Server starts
[ ] Inspector connects
[ ] Capabilities are correct
[ ] Tool metadata is correct
[ ] Valid minimum input passes
[ ] Valid typical input passes
[ ] Boundary input passes
[ ] Invalid input produces a clear error
[ ] Business failure is handled
[ ] Text fallback is useful
[ ] Structured result matches schema
[ ] UI resource URI and MIME type are correct
[ ] App initializes and renders
[ ] Tool input reaches the View
[ ] Tool result reaches the View
[ ] Loading state works
[ ] Empty state works
[ ] Error state works
[ ] Local actions make no server call
[ ] Server actions call the correct tool once
[ ] App-only visibility is enforced
[ ] Theme and resize work
[ ] Display modes degrade gracefully
[ ] Cancellation and teardown work
[ ] CSP blocks undeclared origins
[ ] Permissions are least-privilege
[ ] Keyboard and focus behavior work
[ ] No secrets or stack traces are exposed
[ ] A second host preserves essential behavior

Failures and evidence:

Final result: PASS / FAIL / PASS WITH LIMITATIONS
```

---

## 28. Definition of done

An MCP App is not done merely because its iframe appears. It is ready when:

- The server and transport are reliable.
- Tool and resource contracts are correct.
- Valid, invalid, empty, and failure states are tested.
- The View receives and renders data correctly.
- Every interaction has the intended protocol effect.
- Host context and lifecycle events are handled.
- CSP, permissions, visibility, and authorization use least privilege.
- The UI is usable with keyboard, zoom, and different sizes.
- The tool retains a useful non-UI fallback.
- Essential behavior works in an intended real host.
- Stable protocol checks can be repeated from the CLI or an automated suite.

---

## Professional articulation

> I test MCP Apps in layers: server process, MCP connection, tool and resource
> contracts, iframe lifecycle, bidirectional interaction, host integration,
> resilience, security, accessibility, and cross-host portability. This makes
> failures attributable to a specific boundary instead of treating the App as
> one black box.

**Bidirectional interaction** means the host can deliver input and results to
the App, while the App can request allowed actions from the host.

---

## Official references

- [MCP Apps overview and lifecycle](https://apps.extensions.modelcontextprotocol.io/api/documents/overview.html)
- [Stable MCP Apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- [MCP Inspector documentation](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/tools/inspector.mdx)
- [MCP Inspector CLI documentation](https://github.com/modelcontextprotocol/inspector/blob/main/clients/cli/README.md)
- [Reviewing an MCP App with Inspector](https://github.com/modelcontextprotocol/inspector/blob/main/docs/mcp-app-review.md)
- [Official MCP Apps testing guide](https://github.com/modelcontextprotocol/ext-apps/blob/main/docs/testing-mcp-apps.md)
- [Python SDK MCP Apps implementation](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/apps.py)
