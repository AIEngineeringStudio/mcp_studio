# Lesson 2 — Register a Tool and Its MCP App Resource

## Goal

By the end of this lesson, you should understand this link:

```text
MCP tool
  |
  | resource_uri
  v
MCP App UI resource
```

You will build one small MCP server that exposes:

| Item                           | Purpose                                              |
|--------------------------------|------------------------------------------------------|
| `say_hello` tool               | A normal MCP tool callable by an MCP host            |
| `ui://hello/app.html` resource | The MCP App UI connected to the tool                 |
| `Apps` extension               | The SDK layer that connects the tool and UI resource |

This lesson stays inside **MCP Apps** only. We are **not** using App Bridge yet.

---

## 1. Core idea

An MCP App is not only a frontend.

It is a normal MCP interaction with a UI attached to it.

```text
Tool call
   |
   v
MCP server
   |
   +--> tool result
   |
   +--> linked UI resource
```

The important rule:

```text
The tool advertises the UI resource URI.
The server also registers the actual UI resource.
```

So two things must match:

```text
@apps.tool(resource_uri="ui://hello/app.html")
apps.add_html_resource("ui://hello/app.html", VIEW_HTML)
```

If these two URIs do not match, the host may know that a UI exists, but it cannot fetch the correct UI.

---

## 2. Version choices

Checked on **September 26, 2026**.

| Component       |  Selected version | Why                                                                                                                                              |
|-----------------|------------------:|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Python          |         `3.13.15` | Stable Python 3.13 maintenance release. Python.org says Python 3.13.15 is a maintenance release, while Python 3.14 is the latest feature series. |
| MCP Python SDK  | `mcp[cli]==2.2.0` | Latest listed MCP Python SDK release in GitHub/PyPI results. PyPI marks `2.2.0` as released on Sep 7, 2026 and requiring Python `>=3.10`.        |
| Project manager |              `uv` | `uv` supports pinning Python versions and running commands inside the project environment.                                                       |

Important SDK note:

- MCP Python SDK v2 uses `MCPServer`.
- Older examples may use `FastMCP`.
- The v2 release notes say `FastMCP` is now `MCPServer`.

---

## 3. Project structure

Create this structure:

```text
mcp-apps-learning/
├── .python-version
├── pyproject.toml
├── uv.lock
└── server.py
```

No React yet.

This lesson proves only one concept:

```text
tool registration + UI resource registration
```

---

## 4. Setup commands

Run these commands in order.

```bash
mkdir mcp-apps-learning
cd mcp-apps-learning

uv python pin 3.13.15
uv init --bare
uv add "mcp[cli]==2.2.0"

uv lock
uv sync --locked
```

Check Python:

```bash
uv run --locked python -V
```

Expected output:

```text
Python 3.13.15
```

Check MCP package:

```bash
uv run --locked python -c "import mcp; print(mcp.__version__)"
```

Expected output:

```text
2.2.0
```

---

## 5. Complete runnable code

File path:

```text
mcp-apps-learning/server.py
```

Code:

```python
from mcp.server.apps import Apps
from mcp.server.mcpserver import MCPServer

VIEW_URI = "ui://hello/app.html"

VIEW_HTML = """\
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Hello MCP App</title>
</head>
<body>
    <h1>Hello from an MCP App</h1>
    <p>This HTML came from an MCP resource.</p>
</body>
</html>
"""

apps = Apps()


@apps.tool(
    resource_uri=VIEW_URI,
    description="Return a greeting and display its MCP App UI.",
)
def say_hello() -> str:
    return "Hello from the MCP tool."


apps.add_html_resource(
    VIEW_URI,
    VIEW_HTML,
    title="Hello MCP App",
)

mcp = MCPServer(
    "hello-mcp-app",
    extensions=[apps],
)
```

---

## 6. Run the server

Use:

```bash
uv run --locked mcp run server.py --transport streamable-http
```

Expected result:

```text
The MCP server starts successfully.
The server exposes a tool named say_hello.
The tool is linked to ui://hello/app.html.
The UI resource is registered as HTML.
```

Exact terminal text can vary by SDK version and environment.

The important expected behavior is:

```text
No import error.
No missing dependency error.
No resource registration error.
```

### Inspect the tool and resource

Run:

```bash
uv run --locked mcp dev server.py
```

This starts the server with MCP Inspector, which lets you inspect and call the
registered tool during development.

MCP Inspector is a Node.js application, so `npx` must be available on your
system for this command.

Expected result:

```text
MCP Inspector opens.
Server exposes one tool: say_hello.
The tool is linked to: ui://hello/app.html.
```
---

## 7. Line-by-line walkthrough

### 7.1 Create one resource URI

```python
VIEW_URI = "ui://hello/app.html"
```

This URI is the identity of the UI resource.

Think of it as the internal MCP address for the app UI.

It is not a public website URL.

It is not:

```text
https://...
```

It is:

```text
ui://...
```

---

### 7.2 Create the HTML resource

```python
VIEW_HTML = """\
<!doctype html>
<html lang="en">
...
</html>
"""
```

This is the UI.

In this lesson, the UI is static HTML.

That is intentional.

We are not learning React yet.

---

### 7.3 Create the Apps extension

```python
apps = Apps()
```

`Apps` is the MCP Apps extension helper.

It lets you register:

| Registration                  | Meaning          |
|-------------------------------|------------------|
| `@apps.tool(...)`             | App-aware tool   |
| `apps.add_html_resource(...)` | HTML UI resource |

---

### 7.4 Register the tool

```python
@apps.tool(
    resource_uri=VIEW_URI,
    description="Return a greeting and display its MCP App UI.",
)
def say_hello() -> str:
    return "Hello from the MCP tool."
```

This creates the MCP tool.

The important argument is:

```python
resource_uri = VIEW_URI
```

That connects the tool to the UI resource.

Conceptually, the SDK creates tool metadata like this:

```json
{
  "_meta": {
    "ui": {
      "resourceUri": "ui://hello/app.html"
    }
  }
}
```

The exact SDK internals can change, but the concept is stable:

```text
tool metadata points to the UI resource URI
```

---

### 7.5 Register the UI resource

```python
apps.add_html_resource(
    VIEW_URI,
    VIEW_HTML,
    title="Hello MCP App",
)
```

This registers the actual HTML behind the URI.

Now this URI exists:

```text
ui://hello/app.html
```

Without this line, the tool can point to a URI, but the host cannot fetch the UI.

The SDK serves this resource with the MCP Apps MIME type:

```text
text/html;profile=mcp-app
```

A **MIME type** describes the kind of content in a resource. This value tells
an MCP Apps-capable host that the resource contains an app UI, not ordinary
HTML content that should be treated as a public web page.

---

### 7.6 Attach Apps to the MCP server

```python
mcp = MCPServer(
    "hello-mcp-app",
    extensions=[apps],
)
```

This creates the MCP server and enables the `Apps` extension.

Without:

```python
extensions = [apps]
```

the app-aware tool and resource are not attached to the server.

---

## 8. Runtime flow

When an MCP Apps-capable host calls the tool:

```text
1. Host discovers tools
2. Host sees say_hello
3. Host sees linked resource URI (_meta.ui.resourceUri = ui://hello/app.html
4. Host calls say_hello
5. Server returns the tool result
6. Host sends resources/read for ui://hello/app.html
7. Host renders the HTML in a sandboxed iframe
```

Small diagram:

```text
Host
  |
  | tools/call say_hello
  v
MCPServer
  |
  +--> "Hello from the MCP tool."
  |
  +--> ui://hello/app.html
             |
             v
        HTML UI resource
```

Important boundary:

```text
The server provides the UI resource.
The host renders it.
The iframe displays it.
```

The server does not directly open a browser window.

The server also does not send or receive the UI messages exchanged between the
host and the sandboxed iframe. That communication belongs to the host-side UI
boundary.

---

## 9. Common mistakes

### Mistake 1 — URI mismatch

Bad:

```python
@apps.tool(resource_uri="ui://hello/app.html")
def say_hello() -> str:
    return "Hello"


apps.add_html_resource(
    "ui://different/app.html",
    VIEW_HTML,
    title="Hello MCP App",
)
```

Problem:

```text
The tool points to one URI.
The resource is registered under another URI.
```

Fix:

```python
VIEW_URI = "ui://hello/app.html"


@apps.tool(resource_uri=VIEW_URI)
def say_hello() -> str:
    return "Hello"


apps.add_html_resource(
    VIEW_URI,
    VIEW_HTML,
    title="Hello MCP App",
)
```

Use one shared constant.

---

### Mistake 2 — Forgetting `extensions=[apps]`

Bad:

```python
mcp = MCPServer("hello-mcp-app")
```

Problem:

```text
The Apps extension is created but not attached to the server.
```

Fix:

```python
mcp = MCPServer(
    "hello-mcp-app",
    extensions=[apps],
)
```

---

### Mistake 3 — Using old `FastMCP` examples

Older examples may show:

```python
from mcp.server.fastmcp import FastMCP
```

For this guide, use v2 style:

```python
from mcp.server.mcpserver import MCPServer
```

This avoids mixing old and new SDK patterns.

---

## 10. Professional explanation

Use this wording at work:

> This MCP server registers a normal tool and links it to an MCP App resource using a `ui://` resource URI. The host can
> call the tool, read the linked resource, and render the HTML UI in its own sandboxed app surface.

Shorter version:

> The tool does the work. The `ui://` resource provides the UI. The host connects them.

---

## 11. Practice task

Modify only this line:

```python
VIEW_URI = "ui://hello/app.html"
```

Change it to:

```python
VIEW_URI = "ui://greeting/view.html"
```

Then run:

```bash
uv run --locked mcp run server.py --transport streamable-http
```

Before running, predict:

```text
Will the tool-resource link still work?
Why?
```

Do not change any other code.

The purpose is to test whether you understand why using one shared `VIEW_URI` constant prevents URI mismatch bugs.

---

## 12. Practice extension — customer table

After the URI exercise works, change the app from a greeting to a static
customer-table placeholder.

Change:

```python
VIEW_URI = "ui://greeting/view.html"
```

to:

```python
VIEW_URI = "ui://customers/table.html"
```

In `VIEW_HTML`, replace:

```html
<h1>Hello from an MCP App</h1>
<p>This HTML came from an MCP resource.</p>
```

with:

```html
<h1>Customer Table</h1>
<p>This UI resource will later render customer data.</p>
```

Do not change these references:

```python
@apps.tool(resource_uri=VIEW_URI)
```

```python
apps.add_html_resource(
    VIEW_URI,
    VIEW_HTML,
    title="Hello MCP App",
)
```

Run the server again:

```bash
uv run --locked mcp run server.py --transport streamable-http
```

Then explain in one sentence why the tool-resource link still works after the
URI change.

---

## 13. Checkpoint

You understand Lesson 2 if you can answer these:

1. What does `resource_uri` connect?
2. Why do `@apps.tool(...)` and `apps.add_html_resource(...)` need the same URI?
3. Why is `extensions=[apps]` required?
4. Who renders the UI: the MCP server or the MCP host?
5. Why is `ui://hello/app.html` not the same as a normal public URL?

Expected short answers:

```text
1. The MCP tool to the MCP App UI resource.
2. So the host can fetch the exact UI resource the tool advertises.
3. To attach the Apps extension to the MCP server.
4. The host renders the UI.
5. It is an MCP resource URI, not a public web URL.
```
