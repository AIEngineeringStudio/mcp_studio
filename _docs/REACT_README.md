# React startup from zero

This primer explains how a small React MCP App starts, receives a customer tool result, stores it, and displays it.

## 1. HTML gives React one starting point

The browser loads `index.html` first.

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
inside it.

The script tag loads `App.jsx` as a JavaScript module.

## 2. `createRoot(...).render(...)` starts React

At the bottom of `App.jsx`:

```jsx
createRoot(document.getElementById("root")).render(<CustomerApp/>);
```

Read it from the inside out:

1. `document.getElementById("root")` finds the HTML container.
2. `createRoot(...)` creates a React root attached to that container.
3. `.render(<CustomerApp />)` asks React to display the `CustomerApp` component.

```text
index.html                 App.jsx
<div id="root">  <------  createRoot(...)
                                  |
                                  v
                         render(<CustomerApp />)
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

## 4. `useState` remembers data

Tool data does not exist during the first render, so the component starts with `null`:

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

Instead, React stores `data`, calls `CustomerApp` again, and updates only the DOM that changed.

```text
first render: customer = null  -> "Waiting for customer..."
setCustomer(data)
second render: customer = data -> customer fields appear
```

The basic cycle is:

```
state changes
     |
     v
React calls component again
     |
     v
component returns new UI
     |
     v
browser updates
```

### Where MCP enters

For MCP Apps, the data arrives through an event:

```
MCP Host
   |
   | tool result arrives
   v
MCP App
   |
   | event
   v
our JavaScript handler
   |
   | setCustomer(...)
   v
React
   |
   v
screen updates
```

MCP Apps and React have separate jobs.

| Piece       | Job                         |
|-------------|-----------------------------|
| MCP App SDK | Receive MCP events          |
| React       | Keep UI state and render it |

## 5. Event listeners react to something that happens later

An **event listener** is a function registered now so it can run when an event arrives later.
Meaning:
> When the MCP host sends a `toolresult`, call `handleResult`.

```jsx
function handleResult(result) {
    setCustomer(result.structuredContent);
}

app.addEventListener("toolresult", handleResult);
```

```jsx
app.addEventListener("toolresult", (result) => {
    setCustomer(result.structuredContent);
});
```

This listener waits for a `toolresult` event from the MCP host. The callback receives the result and stores its
structured data in React state.

Runtime:

```
toolresult arrives
       |
       v
handleResult(result)
       |
       v
setCustomer(...)
       |
       v
React re-renders
```

## 6. MCP Apps connection basics

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

The two connections have different responsibilities:

- The UI connects to the **host**.
- The host connects to the **MCP server**.
- The UI does not connect directly to the MCP server.

When the server finishes `get_customer`, the result travels through the host to the UI.

## 7. Where `app.connect()` happens

With the plain SDK, application code connects explicitly:

```javascript
const app = new App(
    {name: "Customer App", version: "1.0.0"},
    {},
);

await app.connect();
```

In React, the `useApp()` hook manages this lifecycle. Your component does not call `app.connect()` directly.

```jsx
const {isConnected, error} = useApp({
    appInfo: {name: "Customer App", version: "1.0.0"},
    capabilities: {},
    onAppCreated: (app) => {
        // Register listeners here.
    },
});
```

The important order is:

```text
useApp()
   |
   v
create App instance (new App(...))
   |
   v
configure App (below two steps are part of configuration)
   |
   +-->call onAppCreated(app)
           |
           v
        register handler/listener
           |
   +-----+ v
   |
   v
app.connect()
   |
   v
UI <----> host connection is ready
```

During connection, the UI and host initialize the MCP Apps session and exchange supported capabilities. Communication
uses a `PostMessageTransport` with the parent host window.

Main steps:
```
1. Connect transport
       |
       v
2. UI sends ui/initialize
       |
       v
3. Host returns capabilities + context
       |
       v
4. UI sends initialized notification
       |
       v
5. App is connected
``` :chatgpt-content-reference{index="2"}
```

After that, the host can send things such as:

```text
toolinput
toolresult
hostcontextchanged
```

### Full Picture

Our application currently has two completely different connections:

```text
                 MCP protocol
MCP Host  <-------------------->  MCP Server
   ^
   |
   | postMessage / MCP Apps protocol
   |
MCP App iframe
```
So when the tool executes:

```text
1. Host calls get_customer() on MCP Server

2. Server returns structuredContent

3. Host receives result

4. Host forwards toolresult event to iframe

5. React MCP App receives toolresult

6. Handler calls:
   setCustomer(result.structuredContent)

7. React re-renders
```

## 8a. Why register `toolresult` before connecting?

The host may send the initial tool result as soon as the connection becomes ready. The listener must already exist.

### Safe order:

The listener should exist before the event can arrive.

```text
Create MCP App object
        |
        v
Register toolresult listener
        |
        v
Connect to host
        |
        v
Host sends toolresult
        |
        v
Listener receives it
```

### Risky order:

```text
Create MCP App object
        |
        v
Connect to host
        |
        v
Host sends toolresult
        |
        v
register listener too late
```

That timing is why `onAppCreated` is useful. It provides the new `App` object before `useApp()` calls `connect()`.

This is not a rule that every React event handler belongs in `onAppCreated`. It is important here because the initial
`toolresult` event can arrive during startup.

## 8b. What is `onAppCreated` then?

Think of `onAppCreated` as:

> "The MCP App object has just been created.
> Here is your chance to configure it
> before it connects."
 
Simplified:
```javascript
useApp({
    onAppCreated: (app) => {
        // app exists here

        app.addEventListener(
            "toolresult",
            handleResult,
        );
    },
});
```
So: That ordering is the important part.
```
useApp()
   |
   +--> creates App object
   |
   +--> calls onAppCreated(app)
   |        |
   |        +--> register listener
   |
   +--> connects app to MCP host
```

## 9. Complete customer component

`src/App.jsx`:

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

## 10. Follow `setCustomer(result.structuredContent)` end to end

The essential version is:

```jsx
app.addEventListener("toolresult", (result) => {
    setCustomer(result.structuredContent);
});
```

Its runtime flow is:

```text
1. MCP server returns a tool result
2. Host receives the result
3. Host sends a toolresult event to the UI
4. The registered listener runs
5. result.structuredContent contains the customer fields
6. setCustomer(...) stores those fields in React state
7. React calls CustomerApp again
8. customer is no longer null
9. JSX reads customer.name, customer.company, and other fields
10. React updates the visible UI
```

`structuredContent` is external input. Validate its fields before displaying or using them, as the complete example
does.

## 11. The whole startup flow

```text
Browser loads index.html
        |
        v
App.jsx finds #root
        |
        v
React renders <CustomerApp />
        |
        v
useState(null): no customer yet
        |
        v
useApp creates the MCP App
        |
        v
onAppCreated registers toolresult
        |
        v
useApp calls app.connect()
        |
        v
UI connects to the host
        |
        v
host sends the customer tool result
        |
        v
listener validates structuredContent
        |
        v
setCustomer(data)
        |
        v
React re-renders and shows the customer
```

## Professional articulation

“The HTML page provides a root DOM node, and React mounts the `CustomerApp` component into it. The MCP Apps `useApp`
hook creates the app, lets us register the initial `toolresult` listener in `onAppCreated`, and then connects the iframe
UI to the host. When the result arrives, `setCustomer` updates state and triggers a re-render.”

## Quick recall

- What does `createRoot(...).render(...)` do? It mounts a React component inside the selected DOM element.
- What does `useState` do? It stores component data between renders.
- What does `setCustomer(...)` do? It replaces the customer state and requests a re-render.
- What does `app.connect()` connect? The MCP App UI to the MCP host.
- Does the UI connect directly to the MCP server? No. The host connects to the server.
- Why use `onAppCreated`? To install the initial result listener before connection.

## References

- [React: State as a Component's Memory](https://react.dev/learn/state-a-components-memory)
- [React: `createRoot`](https://react.dev/reference/react-dom/client/createRoot)
- [OpenAI: Add UI to your MCP server](https://developers.openai.com/plugins/build/chatgpt-ui)
- [MCP Apps SDK source and examples](https://github.com/modelcontextprotocol/ext-apps)
