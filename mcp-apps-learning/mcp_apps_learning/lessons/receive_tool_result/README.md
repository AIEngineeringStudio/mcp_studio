# React startup and the initial MCP tool result

This lesson explains how a React MCP App starts, receives the first `get_customer` result, stores it, and displays it.

It assumes the MCP server already:

- returns a `Customer` with `name`, `company`, `email`, and `status`;
- includes those fields in `structuredContent`; and
- points the tool to a registered `ui://` resource.

## Pinned versions

| Component    |       Pin |
|--------------|----------:|
| Node.js LTS  | `22.22.0` |
| npm          |  `10.9.4` |
| React        |  `19.3.0` |
| React DOM    |  `19.3.0` |
| MCP Apps SDK |   `2.0.3` |
| Vite         |   `8.3.2` |

## UI project structure

```text
mcp-apps-learning/
├── server.py
└── ui/
    ├── package.json
    ├── index.html
    └── src/
        └── App.jsx
```

## 1. HTML gives React a starting point

The browser loads `ui/index.html` first.

```html
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer MCP App</title>
</head>
<body>
<div id="root"></div>
<script type="module" src="/src/App.jsx"></script>
</body>
</html>
```

`<div id="root"></div>` is an empty HTML container. React takes control of this container and places the application UI
inside it. The script tag loads `App.jsx` as a JavaScript module.

## 2. `createRoot(...).render(...)` starts React

At the bottom of `App.jsx`:

```jsx
createRoot(document.getElementById("root")).render(<CustomerApp/>);
```

Read it from the inside out:

1. `document.getElementById("root")` finds the HTML container.
2. `createRoot(...)` creates a React root attached to that container.
3. `.render(<CustomerApp/>)` asks React to display the `CustomerApp` component.

```text
index.html                 App.jsx
<div id="root">  <------  createRoot(...)
                                  |
                                  v
                         render(<CustomerApp/>)
                                  |
                                  v
                         UI appears in the div
```

## 3. A React component is a UI function

A **component** is a JavaScript function that returns JSX. JSX looks like HTML, but it is written inside JavaScript.

```jsx
function CustomerApp() {
    return <h1>Customer</h1>;
}
```

React calls the component to learn what the screen should look like. Component names begin with an uppercase letter.

## 4. `useState` remembers data and causes re-rendering

Customer data does not exist during the first render, so the component starts with `null`:

```jsx
const [customer, setCustomer] = useState(null);
```

| Name             | Purpose                                                           |
|------------------|-------------------------------------------------------------------|
| `customer`       | The current state value. It is `null` at first.                   |
| `setCustomer`    | The function that replaces the value and requests another render. |
| `useState(null)` | Creates this state with an initial value of `null`.               |

Calling a setter does not manually rewrite the HTML:

```jsx
setCustomer(data);
```

React stores `data`, calls `CustomerApp` again, and updates the DOM to match the component's new JSX.

```text
first render:  customer = null  -> "Waiting for customer..."
state update:  setCustomer(data)
second render: customer = data  -> customer fields appear
```

React and the MCP Apps SDK have separate jobs:

| Piece        | Job                              |
|--------------|----------------------------------|
| MCP Apps SDK | Receive events from the MCP host |
| React        | Store UI state and render it     |

## 5. Understand the MCP Apps connections

The MCP App UI runs inside an iframe owned by an MCP host, such as ChatGPT or another MCP Apps-compatible client.

```text
MCP App UI (inside an iframe)
        |
        | MCP Apps JSON-RPC over browser postMessage
        v
MCP host
        |
        | MCP tool and resource requests
        v
MCP server
```

- The UI connects to the **host**.
- The host connects to the **MCP server**.
- The UI does not connect directly to the MCP server.

`app.connect()` creates the UI-to-host connection. During connection:

```text
connect transport
      |
UI sends ui/initialize
      |
host returns capabilities and context
      |
UI sends the initialized notification
      |
connection is ready
```

After connection, the host can send events such as `toolinput`, `toolresult`, and `hostcontextchanged`.

## 6. Where `app.connect()` happens in React

With the plain SDK, application code creates and connects the app explicitly:

```javascript
const app = new App(
    {name: "Customer App", version: "1.0.0"},
    {},
);

await app.connect();
```

In React, the `useApp()` hook manages this lifecycle. The component does not call `app.connect()` directly.

```jsx
const {isConnected, error} = useApp({
    appInfo: {name: "Customer App", version: "1.0.0"},
    capabilities: {},
    onAppCreated: (app) => {
        // Configure the App before connection.
    },
});
```

`useApp()` performs these steps in order:

```text
create App instance
        |
        v
call onAppCreated(app)
        |
        v
register event listeners
        |
        v
call app.connect()
        |
        v
UI-to-host connection is ready
```

`onAppCreated` means: “The `App` object now exists. Configure it before it connects.”

The hook uses a `PostMessageTransport` to communicate with the parent host window. After a successful connection, it
returns the connected `app`, sets `isConnected` to `true`, and keeps any connection failure in `error`.

## 7. Register `toolresult` before connecting

An **event listener** is a function registered now so it can run when an event arrives later.

```jsx
function handleResult(result) {
    setCustomer(result.structuredContent);
}

app.addEventListener("toolresult", handleResult);
```

The host may send the initial tool result as soon as the connection becomes ready. Register the listener inside
`onAppCreated` so it already exists before `useApp()` connects.

```text
Safe:  register listener -> connect -> receive initial result
Risky: connect -> initial result arrives -> register listener too late
```

This is an event-timing requirement. It does not mean that every React event handler must be registered inside
`onAppCreated`.

## 8. Complete customer view

`ui/src/App.jsx`:

```jsx
import {useState} from "react";
import {createRoot} from "react-dom/client";
import {useApp} from "@modelcontextprotocol/ext-apps/react";

function CustomerApp() {
    const [customer, setCustomer] = useState(null);
    const [resultError, setResultError] = useState(null);

    const {isConnected, error} = useApp({
        appInfo: {
            name: "Customer App",
            version: "1.0.0",
        },
        capabilities: {},
        onAppCreated: (app) => {
            app.addEventListener("toolresult", (result) => {
                if (result.isError) {
                    setResultError("The customer tool failed.");
                    return;
                }

                const data = result.structuredContent;

                if (
                    !data ||
                    typeof data.name !== "string" ||
                    typeof data.company !== "string" ||
                    typeof data.email !== "string" ||
                    typeof data.status !== "string"
                ) {
                    setResultError("The customer result has missing fields.");
                    return;
                }

                setResultError(null);
                setCustomer(data);
            });
        },
    });

    if (error) {
        return <p role="alert">Connection error: {error.message}</p>;
    }

    if (!isConnected) {
        return <p>Connecting to host...</p>;
    }

    if (resultError) {
        return <p role="alert">{resultError}</p>;
    }

    if (!customer) {
        return <p>Waiting for customer...</p>;
    }

    return (
        <main>
            <h1>Customer</h1>
            <dl>
                <dt>Name</dt>
                <dd>{customer.name}</dd>

                <dt>Company</dt>
                <dd>{customer.company}</dd>

                <dt>Email</dt>
                <dd>{customer.email}</dd>

                <dt>Status</dt>
                <dd>{customer.status}</dd>
            </dl>
        </main>
    );
}

createRoot(document.getElementById("root")).render(<CustomerApp/>);
```

The current SDK pattern is `addEventListener("toolresult", handler)`. Older examples may use
`app.ontoolresult = handler`; prefer `addEventListener` because it does not replace another registered listener.

### Read the important lines

| Code                                  | Meaning                                                         |
|---------------------------------------|-----------------------------------------------------------------|
| `useState(null)`                      | Remember customer data between renders; start empty.            |
| `useApp({ ... })`                     | Create and connect the MCP App to the host.                     |
| `onAppCreated`                        | Access the new `App` before connection to install the listener. |
| `addEventListener("toolresult", ...)` | Handle the host's completed tool result.                        |
| `result.structuredContent`            | Read the customer's structured fields.                          |
| `setCustomer(data)`                   | Store the fields and request a React re-render.                 |
| `{customer.name}`                     | Display a field from React state in JSX.                        |

## 9. Follow the complete runtime flow

```text
1. The browser loads index.html and App.jsx.
2. React mounts CustomerApp inside #root.
3. CustomerApp renders with customer = null.
4. useApp creates the MCP App object.
5. onAppCreated registers the toolresult listener.
6. useApp connects the UI to the host.
7. The host calls get_customer on the MCP server.
8. The server returns structuredContent to the host.
9. The host sends a toolresult event to the UI.
10. The listener validates result.structuredContent.
11. setCustomer(data) stores the customer in React state.
12. React re-renders CustomerApp and displays the customer fields.
```

`structuredContent` is external input. Validate its fields before displaying or using them, as the complete example
does.

## 10. Build and check this stage

From the existing `ui/` project, use its committed lockfile:

```bash
npm ci
npm run build
```

These commands work unchanged on Intel (`x86_64`) and Apple Silicon (`arm64`) Macs.

Expected result: Vite produces `ui/dist/`. This proves that the React view compiles. It does **not** prove that:

- the MCP host can fetch the built view from the Python `ui://` resource; or
- the host delivered a real `toolresult` event.

Serving the bundled HTML as the MCP App resource is the next integration step.

For a host-level check after that integration, call `get_customer` in an MCP Apps-compatible host. The view should pass
through “Connecting to host...” and “Waiting for customer...”, then display the four customer fields. The waiting state
may pass too quickly to see.

If the flow fails:

- For a connection failure, inspect `error` and the host connection.
- For a tool failure, inspect `result.isError` and the server logs.
- For missing fields, compare `structuredContent` with the component's validation.

## Professional articulation

“The HTML page provides a root DOM node, and React mounts the `CustomerApp` component into it. The MCP Apps `useApp`
hook creates the app, lets us register the initial `toolresult` listener in `onAppCreated`, and then connects the iframe
UI to the host. When the result arrives, `setCustomer` updates state and triggers a re-render.”

## Recall check

- What does `createRoot(...).render(...)` do? It mounts a React component inside the selected DOM element.
- What does `useState` do? It stores component data between renders.
- What does `setCustomer(...)` do? It replaces the customer state and requests a re-render.
- What does `app.connect()` connect? The MCP App UI to the MCP host.
- Does the UI connect directly to the MCP server? No. The host connects to the server.
- Why use `onAppCreated`? To install the initial result listener before connection.

## Official references

- [MCP Apps `useApp` implementation](https://github.com/modelcontextprotocol/ext-apps/blob/main/src/react/useApp.tsx)
- [MCP Apps React example](https://github.com/modelcontextprotocol/ext-apps/blob/main/examples/basic-server-react/src/mcp-app.tsx)
- [MCP Apps tool result notification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx)
- [MCP Apps SDK source](https://github.com/modelcontextprotocol/ext-apps/blob/main/src/app.ts)
- [React state and re-rendering](https://react.dev/learn/state-a-components-memory)
- [React `createRoot`](https://react.dev/reference/react-dom/client/createRoot)
- [MCP Python SDK Apps guide](https://py.sdk.modelcontextprotocol.io/advanced/apps/)
