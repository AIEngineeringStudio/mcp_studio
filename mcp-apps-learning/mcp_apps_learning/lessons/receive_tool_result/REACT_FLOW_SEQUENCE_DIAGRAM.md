# React and MCP App complete sequence

Use this diagram to answer two questions:

1. Which component performs each step?
2. In what order do messages move between the iframe, host, and server?

For application states and decision branches, see
[`REACT_FLOW_DIAGRAMS_CONSOLIDATED.md`](./REACT_FLOW_DIAGRAMS_CONSOLIDATED.md).

## Participants

| Participant     | Responsibility                                                                                    |
|-----------------|---------------------------------------------------------------------------------------------------|
| Browser / React | Render `CustomerApp`, store customer state, and update the DOM.                                   |
| MCP App SDK     | Create the `App`, connect the iframe to the host, and deliver host events to registered handlers. |
| MCP Host        | Own the iframe, communicate with the UI, and use its MCP Client to call the MCP server.           |
| MCP Server      | Run `get_customer()` and return the tool result.                                                  |

The browser UI does not connect directly to the MCP server.

## Complete runtime sequence

The sequence diagrams use a fixed light theme with dark text so their contrast does not depend on the viewer's theme.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", 
"primaryTextColor": "#111827", "primaryBorderColor": "#374151", "lineColor": "#111827", "textColor": "#ffffff", 
"actorBkg": "#98FB98", "actorBorder": "#98FB98", "actorTextColor": "#111827", "actorLineColor": "#6b7280", 
"signalColor": "#DE3163", "signalTextColor": "#ffffff", "labelBoxBkgColor": "#00FFFF", "labelBoxBorderColor": "#00FFFF", 
"labelTextColor": "#111827", "loopTextColor": "#ffffff", "noteBkgColor": "#fef3c7", "noteBorderColor": "#92400e", 
"noteTextColor": "#111827", "activationBkgColor": "#e5e7eb", "activationBorderColor": "#374151", 
"sequenceNumberColor": "#ffffff"}}}%%
sequenceDiagram
    autonumber
    participant UI as Browser / React CustomerApp
    participant SDK as MCP App SDK / useApp
    participant Host as MCP Host
    participant Server as MCP Server

    Note over UI, SDK: 1. Browser and React startup
    UI ->> UI: Load index.html and App.jsx
    UI ->> UI: createRoot(...) renders CustomerApp inside #root
    UI ->> UI: Initialize customer = null and resultError = null
    UI ->> UI: Render Connecting to host...

    Note over UI, SDK: 2. Create and configure the MCP App
    UI ->> SDK: Call useApp({ onAppCreated })
    SDK ->> SDK: Create the MCP App object
    SDK -->> UI: Call onAppCreated(app)
    UI ->> SDK: Register the toolresult listener
    Note over UI, SDK: The listener now exists before connection begins.

    Note over SDK, Host: 3. UI-to-host handshake<br/>MCP Apps JSON-RPC over browser postMessage
    SDK ->> Host: app.connect(): send ui/initialize
    Host -->> SDK: Return capabilities and context
    SDK ->> Host: Send initialized notification

    alt Connection succeeds
        Host -->> SDK: Connection is ready
        SDK -->> UI: Provide the connected App
        UI ->> UI: Render Waiting for customer...
    else Connection fails
        Host --x SDK: Return connection error
        SDK -->> UI: Store the connection error
        UI ->> UI: React renders the connection error alert
    end

    Note over Host, Server: The remaining steps occur only after a successful connection.

    Note over Host, Server: 4. Host-to-server tool call<br/>MCP protocol
    Host ->> Server: MCP Client requests get_customer()
    Server ->> Server: Run get_customer()
    Server -->> Host: Return tool result containing structuredContent

    Note over UI, Host: 5. Deliver the result to the iframe<br/>MCP Apps JSON-RPC over browser postMessage
    Host -->> SDK: Send toolresult event
    SDK -->> UI: Run the registered JavaScript handler with result

    Note over UI: 6. Validate the result and update React
    alt result.isError is true
        UI ->> UI: setResultError("The customer tool failed.")
        UI ->> UI: React renders the result error alert
    else Tool did not report an error
        UI ->> UI: Read result.structuredContent

        alt Required customer fields are missing or invalid
            UI ->> UI: setResultError("The customer result has missing fields.")
            UI ->> UI: React renders the result error alert
        else Customer fields are valid
            UI ->> UI: setResultError(null)
            UI ->> UI: setCustomer(data)
            UI ->> UI: React calls CustomerApp again
            UI ->> UI: CustomerApp returns customer JSX
            UI ->> UI: React updates the DOM
            UI ->> UI: Display name, company, email, and status
        end
    end
```

## Why listener timing matters

The complete sequence uses the safe order:

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", 
"primaryTextColor": "#111827", "primaryBorderColor": "#374151", "lineColor": "#111827", "textColor": "#ffffff", 
"actorBkg": "#98FB98", "actorBorder": "#98FB98", "actorTextColor": "#111827", "actorLineColor": "#6b7280", 
"signalColor": "#DE3163", "signalTextColor": "#ffffff", "labelBoxBkgColor": "#00FFFF", "labelBoxBorderColor": "#00FFFF", 
"labelTextColor": "#111827", "loopTextColor": "#ffffff", "noteBkgColor": "#fef3c7", "noteBorderColor": "#92400e", 
"noteTextColor": "#111827", "activationBkgColor": "#e5e7eb", "activationBorderColor": "#374151", 
"sequenceNumberColor": "#ffffff"}}}%%
sequenceDiagram
    participant UI as React CustomerApp
    participant SDK as MCP App SDK
    participant Host as MCP Host
    UI ->> SDK: Register toolresult listener
    SDK ->> Host: Connect
    Host -->> SDK: Connection ready
    Host -->> SDK: Send initial toolresult
    SDK -->> UI: Run the registered handler
```

The risky order can miss the initial result:

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", 
"primaryTextColor": "#111827", "primaryBorderColor": "#374151", "lineColor": "#111827", "textColor": "#ffffff", 
"actorBkg": "#98FB98", "actorBorder": "#98FB98", "actorTextColor": "#111827", "actorLineColor": "#6b7280", 
"signalColor": "#DE3163", "signalTextColor": "#ffffff", "labelBoxBkgColor": "#00FFFF", "labelBoxBorderColor": "#00FFFF", 
"labelTextColor": "#111827", "loopTextColor": "#ffffff", "noteBkgColor": "#fef3c7", "noteBorderColor": "#92400e", 
"noteTextColor": "#111827", "activationBkgColor": "#e5e7eb", "activationBorderColor": "#374151", 
"sequenceNumberColor": "#ffffff"}}}%%
sequenceDiagram
    participant UI as React CustomerApp
    participant SDK as MCP App SDK
    participant Host as MCP Host
    SDK ->> Host: Connect before registering the listener
    Host -->> SDK: Connection ready
    Host -->> SDK: Send initial toolresult
    Note over UI, SDK: No listener is ready, <br/> so the result can be missed.
    UI ->> SDK: Register listener too late
```

Register the listener inside `onAppCreated`. This callback runs after the `App` object is created and before `useApp`
connects it to the host.
